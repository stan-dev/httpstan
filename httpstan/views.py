"""HTTP request handlers for httpstan.

Handlers are separated from the endpoint names. Endpoints are defined in
`httpstan.routes`.
"""
import asyncio
import functools
import http
import io
import json
import logging
import re
import sqlite3
import traceback
from typing import Optional, Sequence, cast

import aiohttp.web
import webargs.aiohttpparser

import httpstan.cache
import httpstan.fits
import httpstan.models
import httpstan.schemas as schemas
import httpstan.services_stub as services_stub

logger = logging.getLogger("httpstan")


# match a string such as `Iteration: 2000 / 2000 [100%]  (Sampling)`
iteration_info_re = re.compile(rb"Iteration:\s+\d+ / \d+ \[\s*\d+%\]\s+\(\w+\)")


def _make_error(message: str, status: int, details: Optional[Sequence] = None) -> dict:
    status_dict = {"code": status, "status": http.HTTPStatus(status).phrase, "message": message}
    if details is not None:
        status_dict["details"] = details
    return cast(dict, schemas.Status().load(status_dict))


async def handle_health(request: aiohttp.web.Request) -> aiohttp.web.Response:
    """Return 200 OK.

    ---
    get:
      description: Check if service is running.
      responses:
        "200":
          description: OK
    """
    return aiohttp.web.Response(text="httpstan is running.")


async def handle_models(request: aiohttp.web.Request) -> aiohttp.web.Response:
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
          schema: CreateModelRequest
      responses:
        "201":
          description: Identifier for compiled Stan model and compiler output.
          schema: Model
        "400":
          description: Error associated with compile request.
          schema: Status

    """
    args = await webargs.aiohttpparser.parser.parse(schemas.CreateModelRequest(), request)
    # the following block is a hotfix for a webargs issue which
    # should be resolved in 2019, see https://github.com/marshmallow-code/webargs/issues/267
    # remove the block as soon as the issue is fixed (behavior should remain the same)
    import marshmallow.exceptions

    try:
        schemas.CreateModelRequest().load(await request.json())
    except marshmallow.exceptions.ValidationError as ex:
        return aiohttp.web.json_response(ex.messages, status=422)

    program_code = args["program_code"]
    model_name = httpstan.models.calculate_model_name(program_code)
    try:
        module_bytes, compiler_output = await httpstan.cache.load_model_extension_module(model_name, request.app["db"])
    except KeyError:
        logger.info(f"Compiling Stan model, `{model_name}`.")
        try:
            module_bytes, compiler_output = await httpstan.models.compile_model_extension_module(program_code)
        except Exception as exc:
            message, status = f"Failed to compile module: {exc}", 400
            logger.critical(message)
            return aiohttp.web.json_response(_make_error(message, status=status), status=status)
        await httpstan.cache.dump_model_extension_module(model_name, module_bytes, compiler_output, request.app["db"])
    else:
        logger.info(f"Found Stan model in cache (`{model_name}`).")
    response_dict = schemas.Model().load({"name": model_name, "compiler_output": compiler_output})
    return aiohttp.web.json_response(response_dict, status=201)


async def handle_show_params(request: aiohttp.web.Request) -> aiohttp.web.Response:
    """Show parameter names and dimensions.

    Data must be provided as model parameters can and frequently do
    depend on the data.

    ---
    post:
      summary: Get parameter names and dimensions.
      description: >-
        Returns the output of Stan C++ model class methods:
        ``constrained_param_names``, ``get_param_names`` and ``get_dims``.
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
        - in: body
          name: data
          description: >-
              Data for Stan Model. Needed to calculate param names and dimensions.
          required: true
          schema: Data
      responses:
        "200":
          description: Parameters for Stan Model
          schema:
            type: object
            properties:
              id:
                type: string
              params:
                type: array
                items: Parameter
        "400":
          description: Error associated with request.
          schema: Status
        "404":
          description: Model not found.
          schema: Status

    """
    args = await webargs.aiohttpparser.parser.parse(schemas.ShowParamsRequest(), request)
    model_name = f'models/{request.match_info["model_id"]}'
    data = args["data"]

    try:
        model_module, _ = await httpstan.models.import_model_extension_module(model_name, request.app["db"])
    except KeyError:
        message, status = f"Model `{model_name}` not found.", 404
        return aiohttp.web.json_response(_make_error(message, status=status), status=status)

    # ``param_names`` and ``dims`` are defined in ``anonymous_stan_model_services.pyx.template``.
    # Apart from converting C++ types into corresponding Python types, they do no processing of the
    # output of ``get_param_names`` and ``get_dims``.
    # Ignoring types due to the difficulty of referring to an extension module
    # which is compiled during run time.
    try:
        param_names_bytes = model_module.param_names(data)  # type: ignore
    except Exception as exc:
        # e.g., "Found negative dimension size in variable declaration"
        message, status = f"Error calling param_names: `{exc}`", 400
        logger.critical(message)
        return aiohttp.web.json_response(_make_error(message, status=status), status=status)
    param_names = [name.decode() for name in param_names_bytes]
    dims = model_module.dims(data)  # type: ignore
    constrained_param_names_bytes = model_module.constrained_param_names(data)  # type: ignore
    constrained_param_names = [name.decode() for name in constrained_param_names_bytes]
    params = []
    for name, dims_ in zip(param_names, dims):
        constrained_names = tuple(filter(lambda s: re.match(fr"^{name}\.\S+|^{name}\Z", s), constrained_param_names))
        assert isinstance(dims_, list)
        assert constrained_names, constrained_names
        params.append(schemas.Parameter().load({"name": name, "dims": dims_, "constrained_names": constrained_names}))
    return aiohttp.web.json_response({"name": model_name, "params": params})


async def handle_create_fit(request: aiohttp.web.Request) -> aiohttp.web.Response:
    """Call function defined in stan::services.

    ---
    post:
      summary: Call function defined in stan::services.
      description: >-
        ``function`` indicates the name of the ``stan::services function`` which
        should be called given the Stan model associated with the id ``model_id``.
        For example, if sampling using
        ``stan::services::sample::hmc_nuts_diag_e_adapt`` then ``function`` is the full
        function name ``stan::services::sample::hmc_nuts_diag_e_adapt``.  Sampler
        parameters which are not supplied will be given default values taken
        from CmdStan.  For example, if
        ``stan::services::sample::hmc_nuts_diag_e_adapt`` is the function called
        and the parameter ``num_samples`` is not specified, the value 1000 will
        be used. For a full list of default values consult the CmdStan
        documentation.
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
          description: >-
            Full stan::services function name and associated arguments to call with Stan model.
          required: true
          schema: CreateFitRequest
      responses:
        "201":
          description: Identifier for completed Stan fit
          schema: Fit
        "400":
          description: Error associated with request.
          schema: Status
        "404":
          description: Fit not found.
          schema: Status
    """
    model_name = f'models/{request.match_info["model_id"]}'
    args = await webargs.aiohttpparser.parser.parse(schemas.CreateFitRequest(), request)
    # the following block is a hotfix for a webargs issue which
    # should be resolved in 2019, see https://github.com/marshmallow-code/webargs/issues/267
    # remove the block as soon as the issue is fixed (behavior should remain the same)
    import marshmallow.exceptions

    try:
        schemas.CreateFitRequest().load(await request.json())
    except marshmallow.exceptions.ValidationError as ex:
        return aiohttp.web.json_response(ex.messages, status=422)

    try:
        await httpstan.models.import_model_extension_module(model_name, request.app["db"])
    except KeyError:
        message, status = f"Model `{model_name}` not found.", 404
        return aiohttp.web.json_response(_make_error(message, status=status), status=status)

    function = args.pop("function")
    name = httpstan.fits.calculate_fit_name(function, model_name, args)
    try:
        await httpstan.cache.load_fit(name)
    except KeyError:
        pass
    else:
        # cache hit
        operation_name = f'operations/{name.split("/")[-1]}'
        operation_dict = schemas.Operation().load(
            {
                "name": operation_name,
                "done": True,
                "metadata": {"fit": schemas.Fit().load({"name": name})},
                "result": schemas.Fit().load({"name": name}),
            }
        )
        return aiohttp.web.json_response(operation_dict, status=201)

    def _services_call_done(
        operation: dict, messages_file: io.BytesIO, db: sqlite3.Connection, future: asyncio.Future
    ) -> None:
        """Called when services call (i.e., an operation) is done.

        This needs to handle both successful and exception-raising calls.

        Arguments:
            operation: Operation dict
            messages_file: Open file handle passed to services call
            db: Database connection
            future: Finished future

        """
        # either the call succeeded or it raised an exception.
        operation["done"] = True
        messages_file.flush()
        asyncio.ensure_future(httpstan.cache.dump_fit(operation["metadata"]["fit"]["name"], messages_file.getvalue()))
        messages_file.close()

        exc = future.exception()
        if exc:
            # e.g., "hmc_nuts_diag_e_adapt_wrapper() got an unexpected keyword argument, ..."
            # e.g., "Found negative dimension size in variable declaration"
            message, status = (
                f"Exception during call to services function: `{repr(exc)}`, traceback: `{traceback.format_tb(exc.__traceback__)}`",
                400,
            )
            logger.critical(message)
            operation["result"] = _make_error(message, status=status)
        else:
            logger.info(f"Operation `{operation['name']}` finished.")
            operation["result"] = schemas.Fit().load(operation["metadata"]["fit"])

        # store the updated Operation
        operation = schemas.Operation().load(operation)
        asyncio.ensure_future(httpstan.cache.dump_operation(operation["name"], json.dumps(operation).encode(), db))

    operation_name = f'operations/{name.split("/")[-1]}'
    operation_dict = schemas.Operation().load(
        {"name": operation_name, "done": False, "metadata": {"fit": schemas.Fit().load({"name": name})}}
    )
    messages_file = io.BytesIO()

    # Launch the call to the services function in the background. Wire things up
    # such that the database gets updated when the task finishes. Note that
    # if a task is cancelled before finishing a warning will be issued (see
    # `on_cleanup` signal handler in main.py).
    # Note: Python 3.7 and later, `ensure_future` is `create_task`
    def logger_callback(operation: dict, message: bytes) -> None:
        # Hack: Use the raw protobuf-encoded message here. Raw message looks like this:
        # b"\x08\x01\x120\x12.\n,info:Iteration:  500 / 2000 [ 25%]  (Warmup)"
        # Using the raw message avoids having to deserialize the message.
        # Deserializing it would be costly and require importing the protobuf Python module.
        if b"info:Iteration" not in message:
            return
        # When sampling completes rapidly, multiple iteration messages can be passed together. Return the final one.
        operation["metadata"]["progress"] = iteration_info_re.findall(message).pop().decode()
        asyncio.ensure_future(
            httpstan.cache.dump_operation(operation_name, json.dumps(operation_dict).encode(), request.app["db"])
        )

    logger_callback_partial = functools.partial(logger_callback, operation_dict)
    task = asyncio.ensure_future(
        services_stub.call(function, model_name, request.app["db"], messages_file, logger_callback_partial, **args)
    )
    task.add_done_callback(functools.partial(_services_call_done, operation_dict, messages_file, request.app["db"]))
    # keep track of all operations, used by an `on_cleanup` signal handler.
    request.app["operations"].add(operation_name)

    # return the operation
    await httpstan.cache.dump_operation(operation_name, json.dumps(operation_dict).encode(), request.app["db"])
    return aiohttp.web.json_response(operation_dict, status=201)


async def handle_get_fit(request: aiohttp.web.Request) -> aiohttp.web.Response:
    """Get result of a call to a function defined in stan::services.

    ---
    get:
      summary: Get results returned by a function.
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
        "200":
          description: Result as a stream of Protocol Buffer messages.
          schema:
            type: string
            format: binary
        "404":
          description: Fit not found.
          schema: Status
    """
    model_name = f"models/{request.match_info['model_id']}"
    fit_name = f"{model_name}/fits/{request.match_info['fit_id']}"

    try:
        fit_bytes = await httpstan.cache.load_fit(fit_name)
    except KeyError:
        message, status = f"Fit `{fit_name}` not found.", 404
        return aiohttp.web.json_response(_make_error(message, status=status), status=status)
    assert isinstance(fit_bytes, bytes)
    return aiohttp.web.Response(body=fit_bytes)


async def handle_get_operation(request: aiohttp.web.Request) -> aiohttp.web.Response:
    """Get Operation.

    ---
    get:
      summary: Get Operation details.
      description: Return Operation details.
      consumes:
        - application/json
      produces:
        - application/json
      parameters:
        - name: operation_id
          in: path
          description: ID of Operation
          required: true
          type: string
      responses:
        "200":
          description: Operation name and metadata.
          schema: Operation
        "404":
          description: Operation not found.
          schema: Status
    """
    operation_name = f"operations/{request.match_info['operation_id']}"
    try:
        operation = await httpstan.cache.load_operation(operation_name, request.app["db"])
    except KeyError:
        message, status = f"Operation `{operation_name}` not found.", 404
        return aiohttp.web.json_response(_make_error(message, status=status), status=status)
    return aiohttp.web.json_response(operation)
