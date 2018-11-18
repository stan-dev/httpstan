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
from typing import Callable, IO

import google.protobuf.internal.encoder

import httpstan.callbacks_writer_parser
import httpstan.callbacks_writer_pb2 as callbacks_writer_pb2
import httpstan.services.arguments as arguments
import httpstan.spsc_queue
import httpstan.stan


async def call(
    function_name: str,
    model_module,
    data: dict,
    messages_file: IO[bytes],
    logger_callback: Callable = None,
    **kwargs,
):
    """Call stan::services function.

    Yields (asynchronously) messages from the stan::callbacks writers which are
    written to by the stan::services function.

    This is a coroutine function.

    Arguments:
        function_name: full name of function in stan::services
        model_module (module): Stan model extension module
        data: dictionary with data with which to populate array_var_context
        messages_file: file into which length-prefixed messages will be written
        logger_callback: Callback function for logger messages, including sampling progress messages
        kwargs: named stan::services function arguments, see CmdStan documentation.
    """
    method, function_basename = function_name.replace("stan::services::", "").split("::", 1)
    queue_wrapper = httpstan.spsc_queue.SPSCQueue(
        capacity=10_000_000
    )  # 10_000 is enough for ~4000 draws
    array_var_context_capsule = httpstan.stan.make_array_var_context(data)
    # function_basename will be something like "hmc_nuts_diag_e"
    # function_wrapper will refer to a function like "hmc_nuts_diag_e_wrapper"
    function_wrapper = getattr(model_module, function_basename + "_wrapper")

    # Fetch defaults for missing arguments. This is an important piece!
    # For example, `random_seed`, if not in `kwargs`, will be set.
    function_arguments = arguments.function_arguments(function_basename, model_module)
    # This is clumsy due to the way default values are available. There is no
    # way to directly lookup the default value for an argument (e.g., `delta`)
    # given both the argument name and the (full) function name (e.g.,
    # `stan::services::hmc_nuts_diag_e_adapt`).
    for arg in function_arguments:
        if arg not in kwargs:
            kwargs[arg] = arguments.lookup_default(arguments.Method[method.upper()], arg)
    function_wrapper_partial = functools.partial(
        function_wrapper, array_var_context_capsule, queue_wrapper.to_capsule(), **kwargs
    )

    loop = asyncio.get_event_loop()
    future = loop.run_in_executor(None, function_wrapper_partial)  # type: ignore
    parser = httpstan.callbacks_writer_parser.WriterParser()
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
        parsed = parser.parse(message.decode())
        # parsed is None if the message was a blank line or a header with param names
        if parsed:
            if logger_callback and parsed.topic == callbacks_writer_pb2.WriterMessage.Topic.Value(
                "LOGGER"
            ):
                logger_callback(parsed)
            message_bytes = parsed.SerializeToString()
            varint_encoder(messages_file.write, len(message_bytes))
            messages_file.write(message_bytes)
    messages_file.flush()
    # `result()` method will raise exceptions, if any
    future.result()  # type: ignore
