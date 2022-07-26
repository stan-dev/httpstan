"""Call and process output of stan::services functions.

Functions here perform the menial task of calling (from Python) a named C++
function in stan::services given a specific Stan model. The output of the
stan::services function is routed from stan::callbacks writers into Python via a
Unix domain socket.

"""
import asyncio
import collections
import concurrent.futures
import functools
import io
import logging
import multiprocessing as mp
import os
import select
import signal
import socket
import tempfile
import typing
import zlib

import httpstan.cache
import httpstan.models
import httpstan.services.arguments as arguments
from httpstan.config import HTTPSTAN_DEBUG


# Use `get_context` to get a package-specific multiprocessing context.
# See "Contexts and start methods" in the `multiprocessing` docs for details.
def init_worker() -> None:
    signal.signal(signal.SIGINT, signal.SIG_IGN)  # ignore KeyboardInterrupt


executor = concurrent.futures.ProcessPoolExecutor(mp_context=mp.get_context("fork"), initializer=init_worker)
logger = logging.getLogger("httpstan")


# This function belongs inside `_make_lazy_function_wrapper`. It is defined here
# because `pickle` (used by ProcessPoolExecutor) cannot pickle local functions.
def _make_lazy_function_wrapper_helper(
    function_basename: str, model_name: str, *args: typing.Any, **kwargs: typing.Any
) -> typing.Callable:  # pragma: no cover
    services_module = httpstan.models.import_services_extension_module(model_name)
    function = getattr(services_module, function_basename + "_wrapper")
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
    fit_name: str,
    logger_callback: typing.Optional[typing.Callable] = None,
    **kwargs: dict,
) -> None:
    """Call stan::services function.

    Yields (asynchronously) messages from the stan::callbacks writers which are
    written to by the stan::services function.

    This is a coroutine function.

    Arguments:
        function_name: full name of function in stan::services
        services_module (module): model-specific services extension module
        fit_name: Name of fit, used for saving length-prefixed messages
        logger_callback: Callback function for logger messages, including sampling progress messages
        kwargs: named stan::services function arguments, see CmdStan documentation.
    """
    method, function_basename = function_name.replace("stan::services::", "").split("::", 1)

    # Fetch defaults for missing arguments. This is an important step!
    # For example, `random_seed`, if not in `kwargs`, will be set.
    # temporarily load the module to lookup function arguments
    services_module = httpstan.models.import_services_extension_module(model_name)
    function_arguments = arguments.function_arguments(function_basename, services_module)
    del services_module
    # This is clumsy due to the way default values are available. There is no
    # way to directly lookup the default value for an argument (e.g., `delta`)
    # given both the argument name and the (full) function name (e.g.,
    # `stan::services::hmc_nuts_diag_e_adapt`).
    for arg in function_arguments:
        if arg not in kwargs:
            kwargs[arg] = typing.cast(typing.Any, arguments.lookup_default(arguments.Method[method.upper()], arg))

    with socket.socket(socket.AF_UNIX, type=socket.SOCK_STREAM) as socket_:
        temp_fd, socket_filename = tempfile.mkstemp(prefix="httpstan_", suffix=".sock")
        os.close(temp_fd)
        os.unlink(socket_filename)
        socket_.bind(socket_filename)
        socket_.listen(4)  # three stan callback writers, one stan callback logger

        lazy_function_wrapper = _make_lazy_function_wrapper(function_basename, model_name)
        lazy_function_wrapper_partial = functools.partial(lazy_function_wrapper, socket_filename, **kwargs)

        # If HTTPSTAN_DEBUG is set block until sampling is complete. Do not use an executor.
        if HTTPSTAN_DEBUG:  # pragma: no cover
            future: asyncio.Future = asyncio.Future()
            logger.debug("Calling stan::services function with debug mode on.")
            print("Warning: httpstan debug mode is on! `num_samples` must be set to a small number (e.g., 10).")
            future.set_result(lazy_function_wrapper_partial())
        else:
            future = asyncio.get_running_loop().run_in_executor(executor, lazy_function_wrapper_partial)  # type: ignore

        messages_files: typing.Mapping[socket.socket, io.BytesIO] = collections.defaultdict(io.BytesIO)
        # using a wbits value which makes things compatible with gzip
        messages_compressobjs: typing.Mapping[socket.socket, zlib._Compress] = collections.defaultdict(
            functools.partial(zlib.compressobj, level=zlib.Z_BEST_SPEED, wbits=zlib.MAX_WBITS | 16)
        )
        potential_readers = [socket_]

        while True:
            # note: timeout of 0.01 seems to work well based on measurements
            readable, writeable, errored = select.select(potential_readers, [], [], 0.01)
            for s in readable:
                if s is socket_:
                    conn, _ = s.accept()
                    logger.debug("Opened socket connection to a socket_logger or socket_writer.")
                    potential_readers.append(conn)
                    continue
                message = s.recv(8192)
                if not len(message):
                    # `close` called on other end
                    s.close()
                    logger.debug("Closed socket connection to a socket_logger or socket_writer.")
                    potential_readers.remove(s)
                    continue
                # Only trigger callback if message has topic `logger`.
                if logger_callback and b'"logger"' in message:
                    logger_callback(message)
                messages_files[s].write(messages_compressobjs[s].compress(message))
            # if `potential_readers == [socket_]` then either (1) no connections
            # have been opened or (2) all connections have been closed.
            if not readable:
                if potential_readers == [socket_] and future.done():
                    logger.debug(
                        f"Stan services function `{function_basename}` returned without problems or raised a C++ exception."
                    )
                    break
                # no messages right now and not done. Sleep briefly so other pending tasks get a chance to run.
                await asyncio.sleep(0.001)

    compressed_parts = []
    for s, fh in messages_files.items():
        fh.write(messages_compressobjs[s].flush())
        fh.flush()
        compressed_parts.append(fh.getvalue())
        fh.close()
    httpstan.cache.dump_fit(b"".join(compressed_parts), fit_name)

    # if an exception has already occurred, grab relevant info messages, add as context
    exception = future.exception()
    if exception and len(exception.args) == 1:
        import gzip
        import json

        original_exception_message = exception.args[0]  # e.g., from ValueError("Initialization failed.")
        info_messages_for_context = []
        num_context_messages = 4

        jsonlines = gzip.decompress(b"".join(compressed_parts)).decode()
        for line in jsonlines.split("\n")[:num_context_messages]:
            try:
                message = json.loads(line)
                info_message = message["values"].pop().replace("info:", "")
                info_messages_for_context.append(info_message.strip())
            except json.JSONDecodeError:
                pass
        # add the info messages to the original exception message. For example,
        # ValueError("Initialization failed.") -> ValueError("Initialization failed. Rejecting initial value: Log probability ...")
        if info_messages_for_context:
            new_exception_message = f"{original_exception_message} {' '.join(info_messages_for_context)} ..."
            exception.args = (new_exception_message,)

    # `result()` method will raise exceptions, if any
    future.result()
