"""Call and process output of stan::services functions.

Functions here perform the menial task of calling (from Python) a named C++
function in stan::services given a specific Stan model. The output of the
stan::services function is routed from stan::callbacks writers into Python via a
Unix domain socket.

"""
import asyncio
import concurrent.futures
import functools
import socket
import sqlite3
import tempfile
import typing
import os

import httpstan.cache
import httpstan.models
import httpstan.services.arguments as arguments

executor = concurrent.futures.ProcessPoolExecutor()


# This function belongs inside `_make_lazy_function_wrapper`. It is defined here
# because `pickle` (used by ProcessPoolExecutor) cannot pickle local functions.
def _make_lazy_function_wrapper_helper(
    function_basename: str, model_name: str, *args: typing.Any, **kwargs: typing.Any
) -> typing.Callable:
    cache_filename = httpstan.cache.cache_filename()
    conn = sqlite3.connect(cache_filename)
    model_module, _ = asyncio.run(httpstan.models.import_model_extension_module(model_name, conn))
    function = getattr(model_module, function_basename + "_wrapper")
    return function(*args, **kwargs)  # type: ignore


# In order to avoid problems with the ProcessPoolExecutor, the module
# needs to be loaded inside the spawned process, not before.
def _make_lazy_function_wrapper(function_basename: str, model_name: str) -> typing.Callable:
    # function_basename will be something like "hmc_nuts_diag_e"
    # function_wrapper will refer to a function like "hmc_nuts_diag_e_wrapper"
    return functools.partial(_make_lazy_function_wrapper_helper, function_basename, model_name)


async def call(
    function_name: str,
    model_name: str,
    db: sqlite3.Connection,
    messages_file: typing.IO[bytes],
    logger_callback: typing.Optional[typing.Callable] = None,
    **kwargs: dict,
) -> None:
    """Call stan::services function.

    Yields (asynchronously) messages from the stan::callbacks writers which are
    written to by the stan::services function.

    This is a coroutine function.

    Arguments:
        function_name: full name of function in stan::services
        model_module (module): Stan model extension module
        messages_file: file into which length-prefixed messages will be written
        logger_callback: Callback function for logger messages, including sampling progress messages
        kwargs: named stan::services function arguments, see CmdStan documentation.
    """
    method, function_basename = function_name.replace("stan::services::", "").split("::", 1)

    # Fetch defaults for missing arguments. This is an important step!
    # For example, `random_seed`, if not in `kwargs`, will be set.
    # temporarily load the module to lookup function arguments
    model_module, _ = await httpstan.models.import_model_extension_module(model_name, db)
    function_arguments = arguments.function_arguments(function_basename, model_module)
    del model_module
    # This is clumsy due to the way default values are available. There is no
    # way to directly lookup the default value for an argument (e.g., `delta`)
    # given both the argument name and the (full) function name (e.g.,
    # `stan::services::hmc_nuts_diag_e_adapt`).
    for arg in function_arguments:
        if arg not in kwargs:
            kwargs[arg] = typing.cast(typing.Any, arguments.lookup_default(arguments.Method[method.upper()], arg))

    with socket.socket(socket.AF_UNIX, type=socket.SOCK_DGRAM) as socket_:
        _, socket_filename = tempfile.mkstemp(prefix="httpstan_", suffix=".sock")
        os.unlink(socket_filename)
        socket_.settimeout(0.001)
        socket_.bind(socket_filename)

        lazy_function_wrapper = _make_lazy_function_wrapper(function_basename, model_name)
        lazy_function_wrapper_partial = functools.partial(lazy_function_wrapper, socket_filename.encode(), **kwargs)
        future = asyncio.get_running_loop().run_in_executor(executor, lazy_function_wrapper_partial)

        while True:
            try:
                message = socket_.recv(8192)
            except socket.timeout:
                if future.done():  # type: ignore
                    break  # exit while loop
                await asyncio.sleep(0.1)
                continue
            if logger_callback and message[1:].startswith(b"\x08\x01"):
                logger_callback(message)
            messages_file.write(message)
    messages_file.flush()
    # `result()` method will raise exceptions, if any
    future.result()  # type: ignore
