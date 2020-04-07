"""Call and process output of stan::services functions.

Functions here perform the menial task of calling (from Python) a named C++
function in stan::services given a specific Stan model. The output of the
stan::services function is routed from stan::callbacks writers into Python via a
queue. The queue is a lock-free single-producer/single-consumer queue defined in
<boost/lockfree/spsc_queue.hpp>.
"""
import asyncio
import functools
import queue  # for queue.Empty exception
import types
import typing

import google.protobuf.internal.encoder

import httpstan.services.arguments as arguments


async def call(
    function_name: str,
    model_module: types.ModuleType,
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
    # queue capacity of 10_000_000 is enough for ~4_000_000 draws. Type ignored
    # because SPSCQueue is part of a module which is compiled during run time.
    queue_wrapper = model_module.SPSCQueue(capacity=10_000_000)  # type: ignore
    # function_basename will be something like "hmc_nuts_diag_e"
    # function_wrapper will refer to a function like "hmc_nuts_diag_e_wrapper"
    function_wrapper = getattr(model_module, function_basename + "_wrapper")

    # Fetch defaults for missing arguments. This is an important step!
    # For example, `random_seed`, if not in `kwargs`, will be set.
    function_arguments = arguments.function_arguments(function_basename, model_module)
    # This is clumsy due to the way default values are available. There is no
    # way to directly lookup the default value for an argument (e.g., `delta`)
    # given both the argument name and the (full) function name (e.g.,
    # `stan::services::hmc_nuts_diag_e_adapt`).
    for arg in function_arguments:
        if arg not in kwargs:
            kwargs[arg] = typing.cast(typing.Any, arguments.lookup_default(arguments.Method[method.upper()], arg))
    function_wrapper_partial = functools.partial(function_wrapper, queue_wrapper, **kwargs)

    loop = asyncio.get_event_loop()
    future = loop.run_in_executor(None, function_wrapper_partial)
    # `varint_encoder` is used here as part of a simple strategy for storing
    # a sequence of protocol buffer messages. Each message is prefixed by the
    # length of a message. This works and is Google's recommended approach.
    varint_encoder = google.protobuf.internal.encoder._EncodeVarint  # type: ignore
    while True:
        try:
            message = queue_wrapper.get_nowait()
        except queue.Empty:
            if future.done():  # type: ignore
                break
            await asyncio.sleep(0.1)
            continue
        # Only trigger callback if message has topic LOGGER. Topic is an
        # Enum:
        # enum Topic {
        #   UNKNOWN = 0;
        #   LOGGER = 1;          // logger messages
        #   INITIALIZATION = 2;  // unconstrained inits
        #   SAMPLE = 3;          // draws
        #   DIAGNOSTIC = 4;      // diagnostic information
        # }
        # b'\0x08\x01' is how messages with Topic 1 (LOGGER) start
        if logger_callback and message.startswith(b"\x08\x01"):
            logger_callback(message)
        varint_encoder(messages_file.write, len(message))
        messages_file.write(message)
    messages_file.flush()
    # `result()` method will raise exceptions, if any
    future.result()  # type: ignore
