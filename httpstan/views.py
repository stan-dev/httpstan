"""HTTP request handlers for httpstan.

Handlers are separated from the endpoint names. Endpoints are defined in
`httpstan.routes`.
"""
import json
import logging
import re

import aiohttp.web
import google.protobuf.json_format
import marshmallow
import marshmallow.fields as fields
import marshmallow.validate as validate
import webargs.aiohttpparser

import httpstan.cache
import httpstan.models
import httpstan.services_stub as services_stub

logger = logging.getLogger("httpstan")


def json_error(message: str) -> aiohttp.web.Response:  # noqa
    return aiohttp.web.Response(
        body=json.dumps({"error": message}).encode("utf-8"), content_type="application/json"
    )


models_args = {"program_code": fields.Str(required=True)}


class ModelSchema(marshmallow.Schema):  # noqa
    id = fields.String(required=True)

    class Meta:  # noqa
        strict = True


class ErrorSchema(marshmallow.Schema):  # noqa
    """Serialize a Python Exception into JSON."""

    type = fields.String(required=True)
    message = fields.String(required=True)

    class Meta:  # noqa
        strict = True


async def handle_health(request):
    """Return 200 OK.

    ---
    get:
        description: Check if service is running.
    """
    return aiohttp.web.Response(text="httpstan is running.")


async def handle_models(request):
    """Compile Stan model.

    ---
    post:
        description: Compile a Stan model
        consumes:
            - application/json
        produces:
            - application/json
        parameters:
            - in: body
              name: body
              description: Stan program code to compile
              required: true
              schema:
                  type: object
                  properties:
                      program_code:
                          type: string
        responses:
            200:
              description: Identifier for compiled Stan model
              schema:
                 $ref: '#/definitions/Model'
            400:
              description: Error associated with compile request.
              schema:
                 $ref: '#/definitions/Error'

    """
    args = await webargs.aiohttpparser.parser.parse(models_args, request)
    program_code = args["program_code"]
    model_id = httpstan.models.calculate_model_id(program_code)
    try:
        module_bytes = await httpstan.cache.load_model_extension_module(model_id, request.app["db"])
    except KeyError:
        logger.info("Compiling Stan model. Model id is {}.".format(model_id))
        try:
            module_bytes = await httpstan.models.compile_model_extension_module(program_code)
        except Exception as exc:
            return aiohttp.web.json_response(
                ErrorSchema().dump({"type": type(exc).__name__, "message": str(exc)}).data,
                status=400,
            )
        await httpstan.cache.dump_model_extension_module(model_id, module_bytes, request.app["db"])
    else:
        logger.info("Found Stan model in cache. Model id is {}.".format(model_id))
    return aiohttp.web.json_response(ModelSchema().dump({"id": model_id}).data)


# TODO(AR): supported functions can be fetched from stub Python files
FUNCTION_NAMES = frozenset(
    {"stan::services::sample::hmc_nuts_diag_e", "stan::services::sample::hmc_nuts_diag_e_adapt"}
)


class ModelsActionSchema(marshmallow.Schema):  # noqa
    # action `type` is full name of function in stan::services (e.g.,
    # `stan::services::sample::hmc_nuts_diag_e_adapt`)
    type = fields.String(required=True, validate=validate.OneOf(FUNCTION_NAMES))
    data = fields.Dict(missing={})

    class Meta:  # noqa
        strict = True


async def handle_models_actions(request):
    """Call function defined in stan::services.

    ---
    post:
        summary: Call function defined in stan::services.
        description: >
            The action `type` indicates the name of the stan::services function
            which should be called given the Stan model associated with the id
            `model_id`.  For example, if sampling using
            ``stan::services::sample::hmc_nuts_diag_e`` the action `type` is the
            full function name ``stan::services::sample::hmc_nuts_diag_e``.
        consumes:
            - application/json
        produces:
            - application/x-ndjson
        parameters:
            - name: model_id
              in: path
              description: ID of Stan model to use
              required: true
              type: string
            - name: body
              in: body
              description: "'Action' specifying full stan::services function name to call with Stan model."
              required: true
              schema:
                 $ref: '#/definitions/ModelsAction'
        responses:
            200:
                description: Stream of newline-delimited JSON.
    """
    model_id = request.match_info["model_id"]
    # use webargs to make sure `type` is present and data is a mapping (or
    # absent). Do not discard any other information in the request body.
    kwargs_schema = await webargs.aiohttpparser.parser.parse(ModelsActionSchema(), request)
    kwargs = await request.json()
    kwargs.update(kwargs_schema)

    module_bytes = await httpstan.cache.load_model_extension_module(model_id, request.app["db"])
    if module_bytes is None:
        return json_error("Stan model with id `{}` not found.".format(model_id))
    model_module = httpstan.models.load_model_extension_module(model_id, module_bytes)

    # setup streaming response
    stream = aiohttp.web.StreamResponse()
    stream.content_type = "application/json"
    stream.charset = "utf-8"
    stream.enable_chunked_encoding()
    await stream.prepare(request)

    type, data = kwargs.pop("type"), kwargs.pop("data")
    async for message in services_stub.call(type, model_module, data, **kwargs):
        assert message is not None, message
        await stream.write(
            google.protobuf.json_format.MessageToJson(message).encode().replace(b"\n", b"")
        )
        await stream.write(b"\n")
    return stream


models_params_args = {"data": fields.Dict(required=True)}


class ParamSchema(marshmallow.Schema):  # noqa
    """Schema for single parameter."""

    name = fields.String(required=True)
    dims = fields.List(fields.Integer(), required=True)
    constrained_names = fields.List(fields.String(), required=True)

    class Meta:  # noqa
        strict = True


async def handle_models_params(request):
    """Get parameter names and dimensions.

    Data must be provided as model parameters can and frequently do
    depend on the data.

    ---
    post:
        summary: Get parameter names and dimensions.
        description: >
            Returns, wrapped in JSON, the output of Stan C++ model class
            methods: ``constrained_param_names``, ``get_param_names`` and ``get_dims``.
        consumes:
            - application/json
        produces:
            - application/json
        parameters:
            - name: model_id
              in: path
              description: ID of Stan model to use
              required: true
              type: string
            - name: body
              in: body
              description: >
                  Data for Stan Model. Needed to calculate param names and dimensions.
              required: true
              schema:
                  type: object
                  properties:
                      data:
                          type: object
        responses:
            200:
              description: Parameters for Stan Model
              schema:
                  type: object
                  properties:
                      id:
                          type: string
                      params:
                          type: array
                          items:
                              $ref: '#/definitions/ParamSchema'
    """
    args = await webargs.aiohttpparser.parser.parse(models_params_args, request)
    model_id = request.match_info["model_id"]
    data = args["data"]

    module_bytes = await httpstan.cache.load_model_extension_module(model_id, request.app["db"])
    if module_bytes is None:
        return json_error("Stan model with id `{}` not found.".format(model_id))
    model_module = httpstan.models.load_model_extension_module(model_id, module_bytes)

    array_var_context_capsule = httpstan.stan.make_array_var_context(data)
    # ``param_names`` and ``dims`` are defined in ``anonymous_stan_model_services.pyx.template``.
    # Apart from converting C++ types into corresponding Python types, they do no processing of the
    # output of ``get_param_names`` and ``get_dims``.
    param_names_bytes = model_module.param_names(array_var_context_capsule)
    param_names = [name.decode() for name in param_names_bytes]
    dims = model_module.dims(array_var_context_capsule)
    constrained_param_names_bytes = model_module.constrained_param_names(array_var_context_capsule)
    constrained_param_names = [name.decode() for name in constrained_param_names_bytes]
    params = []
    for name, dims_ in zip(param_names, dims):
        constrained_names = tuple(
            filter(lambda s: re.match(fr"{name}\.?", s), constrained_param_names)
        )
        assert isinstance(dims_, list)
        assert constrained_names, constrained_names
        params.append(
            ParamSchema()
            .dump({"name": name, "dims": dims_, "constrained_names": constrained_names})
            .data
        )
    return aiohttp.web.json_response({"id": model_id, "params": params})
