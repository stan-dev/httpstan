"""Call and process output of stan::services functions.

Functions here perform the menial task of calling (from Python) a named C++
function in stan::services given a specific Stan model. The output of the
stan::services function is routed from stan::callbacks writers into Python via a
Unix domain socket.

"""
import asyncio
import concurrent.futures
import functools
import logging
import os
import select
import socket
import sqlite3
import tempfile
import typing

import httpstan.cache
import httpstan.models
import httpstan.services.arguments as arguments

executor = concurrent.futures.ProcessPoolExecutor()
logger = logging.getLogger("httpstan")


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

    with socket.socket(socket.AF_UNIX, type=socket.SOCK_STREAM) as socket_:
        _, socket_filename = tempfile.mkstemp(prefix="httpstan_", suffix=".sock")
        os.unlink(socket_filename)
        socket_.bind(socket_filename)
        socket_.listen(4)  # three stan callback writers, one stan callback logger

        lazy_function_wrapper = _make_lazy_function_wrapper(function_basename, model_name)
        lazy_function_wrapper_partial = functools.partial(lazy_function_wrapper, socket_filename.encode(), **kwargs)
        future = asyncio.get_running_loop().run_in_executor(executor, lazy_function_wrapper_partial)

        potential_readers = [socket_]
        while True:
            # note: timeout of 0 required to avoid blocking
            readable, writeable, errored = select.select(potential_readers, [], [], 0)
            for s in readable:
                if s is socket_:
                    conn, _ = s.accept()
                    logger.debug("Opened socket connection to a socket_logger or socket_writer.")
                    potential_readers.append(conn)
                    continue
                message = s.recv(1024 * 256)
                if not len(message):
                    # `close` called on other end
                    s.close()
                    logger.debug("Closed socket connection to a socket_logger or socket_writer.")
                    potential_readers.remove(s)
                    continue
                # Only trigger callback if message has topic LOGGER.  b'\0x08\x01' is how messages with Topic 1 (LOGGER) start.
                # With length-prefix encoding a logger message looks like:
                # b'6\x08\x01\x122\x120\n.info:Iteration: 2000 / 2000 [100%] (Sampling)' where b'6' indicates message length
                if logger_callback and message[1:].startswith(b"\x08\x01"):
                    logger_callback(message)
                messages_file.write(message)
            # if `potential_readers == [socket_]` then either (1) no connections
            # have been opened or (2) all connections have been closed.
            if not readable and potential_readers == [socket_]:
                if future.done():  # type: ignore
                    logger.debug(f"Stan services function `{function_basename}` returned or raised a C++ exception.")
                    break
                await asyncio.sleep(0.01)
    # `result()` method will raise exceptions, if any
    future.result()  # type: ignore
