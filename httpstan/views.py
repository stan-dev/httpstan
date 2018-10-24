"""HTTP request handlers for httpstan.

Handlers are separated from the endpoint names. Endpoints are defined in
`httpstan.routes`.
"""
import io
import http
import logging
import re

import aiohttp.web
import google.protobuf.internal.encoder
import google.protobuf.json_format
import webargs.aiohttpparser
from typing import Optional, Sequence

import httpstan.cache
import httpstan.fits
import httpstan.models
import httpstan.schemas as schemas
import httpstan.services_stub as services_stub

logger = logging.getLogger("httpstan")


def _make_error(message: str, status: int, details: Optional[Sequence] = None) -> dict:
    status_dict = {"code": status, "status": http.HTTPStatus(status).phrase, "message": message}
    if details is not None:
        status_dict["details"] = details
    status = schemas.Status().load(status_dict)
    return schemas.Error().load({"error": status})


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
            201:
              description: Identifier for compiled Stan model
              schema:
                 $ref: '#/definitions/Model'
            400:
              description: Error associated with compile request.
              schema:
                 $ref: '#/definitions/Error'

    """
    args = await webargs.aiohttpparser.parser.parse(schemas.CreateModelRequest(), request)
    program_code = args["program_code"]
    model_name = httpstan.models.calculate_model_name(program_code)
    try:
        module_bytes = await httpstan.cache.load_model_extension_module(
            model_name, request.app["db"]
        )
    except KeyError:
        logger.info("Compiling Stan model, `{model_name}`.")
        try:
            module_bytes = await httpstan.models.compile_model_extension_module(program_code)
        except Exception as exc:
            message, status = f"Failed to compile module. Exception: {exc}", 400
            logger.critical(message)
            return aiohttp.web.json_response(_make_error(message, status=status), status=status)
        await httpstan.cache.dump_model_extension_module(
            model_name, module_bytes, request.app["db"]
        )
    else:
        logger.info(f"Found Stan model in cache (`{model_name}`).")
    return aiohttp.web.json_response(schemas.Model().load({"name": model_name}), status=201)


async def handle_show_params(request):
    """Show parameter names and dimensions.

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
                              $ref: '#/definitions/Parameter'
    """
    args = await webargs.aiohttpparser.parser.parse(schemas.ShowParamsRequest(), request)
    model_name = f'models/{request.match_info["model_id"]}'
    data = args["data"]

    module_bytes = await httpstan.cache.load_model_extension_module(model_name, request.app["db"])
    if module_bytes is None:
        message, status = f"Model `{model_name}` not found.", 404
        return aiohttp.web.json_response(_make_error(message, status=status), status=status)

    model_module = httpstan.models.import_model_extension_module(model_name, module_bytes)

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
            schemas.Parameter().load(
                {"name": name, "dims": dims_, "constrained_names": constrained_names}
            )
        )
    return aiohttp.web.json_response({"name": model_name, "params": params})


async def handle_create_fit(request):
    """Call function defined in stan::services.

    ---
    post:
        summary: Call function defined in stan::services.
        description: >
            `function` indicates the name of the stan::services function
            which should be called given the Stan model associated with the id
            `model_id`.  For example, if sampling using
            ``stan::services::sample::hmc_nuts_diag_e`` then `function` is the
            full function name ``stan::services::sample::hmc_nuts_diag_e``.
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
              description: "Full stan::services function name to call with Stan model."
              required: true
              schema:
                 $ref: '#/definitions/CreateFitRequest'
        responses:
            201:
              description: Identifier for completed Stan fit
              schema:
                 $ref: '#/definitions/Fit'
            400:
              description: Error associated with request.
              schema:
                 $ref: '#/definitions/Error'
    """
    model_name = f'models/{request.match_info["model_id"]}'
    # use webargs to make sure `function` is present and data is a mapping (or
    # absent). Do not discard any other information in the request body.
    kwargs_schema = await webargs.aiohttpparser.parser.parse(schemas.CreateFitRequest(), request)
    kwargs = await request.json()
    kwargs.update(kwargs_schema)

    module_bytes = await httpstan.cache.load_model_extension_module(model_name, request.app["db"])
    if module_bytes is None:
        message, status = f"Model `{model_name}` not found.", 404
        return aiohttp.web.json_response(_make_error(message, status=status), status=status)
    model_module = httpstan.models.import_model_extension_module(model_name, module_bytes)

    function, data = kwargs.pop("function"), kwargs.pop("data")
    name = httpstan.fits.calculate_fit_name(function, model_name, data, kwargs)
    try:
        await httpstan.cache.load_fit(name, model_name, request.app["db"])
    except KeyError:
        pass
    else:
        return aiohttp.web.json_response(schemas.Fit().load({"name": name}), status=201)

    messages_fh = io.BytesIO()

    # `varint_encoder` is used here as part of a simple strategy for storing
    # a sequence of protocol buffer messages. Each message is prefixed by the
    # length of a message. This works and is Google's recommended approach.
    varint_encoder = google.protobuf.internal.encoder._EncodeVarint
    async for message in services_stub.call(function, model_module, data, **kwargs):
        assert message is not None, message
        message_bytes = message.SerializeToString()
        varint_encoder(messages_fh.write, len(message_bytes))
        messages_fh.write(message_bytes)
    await httpstan.cache.dump_fit(name, messages_fh.getvalue(), model_name, request.app["db"])
    return aiohttp.web.json_response(schemas.Fit().load({"name": name}), status=201)


async def handle_get_fit(request):
    """Get result of a call to a function defined in stan::services.

    ---
    get:
        description: Result (e.g., draws) from calling a function defined in stan::services.
        consumes:
            - application/json
        produces:
            - application/octet-stream
        parameters:
            - name: model_id
              in: path
              description: ID of Stan model associated with the result
              required: true
              type: string
            - name: fit_id
              in: path
              description: ID of Stan result ("fit") desired
              required: true
              type: string
        responses:
            200:
              description: Result as a stream of Protocol Buffer messages.
            404:
              description: Error associated with request.
              schema:
                 $ref: '#/definitions/Error'
    """
    model_name = f"models/{request.match_info['model_id']}"
    fit_name = f"{model_name}/fits/{request.match_info['fit_id']}"

    try:
        fit_bytes = await httpstan.cache.load_fit(fit_name, model_name, request.app["db"])
    except KeyError:
        message, status = f"Fit `{fit_name}` not found.", 404
        return aiohttp.web.json_response(_make_error(message, status=status), status=status)
    assert isinstance(fit_bytes, bytes)
    return aiohttp.web.Response(body=fit_bytes)
