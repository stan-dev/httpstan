"""Call and process output of stan::services functions.

Functions here perform the menial task of calling (from Python) a named C++
function in stan::services given a specific Stan Program. The output of the
stan::services function is routed from stan::callbacks writers into Python via a
queue. The queue is a lock-free single-producer/single-consumer queue defined in
<boost/lockfree/spsc_queue.hpp>.
"""
import asyncio
import functools
import queue  # for queue.Empty exception

import httpstan.callbacks_writer_parser
import httpstan.services.arguments as arguments
import httpstan.spsc_queue
import httpstan.stan


async def call(function_name: str, program_module, data: dict, **kwargs):
    """Call stan::services function.

    Yields (asynchronously) messages from the stan::callbacks writers which are
    written to by the stan::services function.

    This is a coroutine function.

    Arguments:
        function_name: full name of function in stan::services
        program_module (module): Stan Program extension module
        data: dictionary with data with which to populate array_var_context
        kwargs: named stan::services function arguments, see CmdStan documentation.
    """
    method, function_basename = function_name.replace('stan::services::', '').split('::', 1)
    queue_wrapper = httpstan.spsc_queue.SPSCQueue(capacity=10000)
    array_var_context_capsule = httpstan.stan.make_array_var_context(data)
    function_wrapper = getattr(program_module, function_basename + '_wrapper')

    # fetch defaults for missing arguments
    function_arguments = arguments.function_arguments(function_basename, program_module)
    # This is clumsy due to the way default values are available. There is no
    # way to directly lookup the default value for an argument (e.g., `delta`)
    # given both the argument name and the (full) function name (e.g.,
    # `stan::services::hmc_nuts_diag_e_adapt`).
    for arg in function_arguments:
        if arg not in kwargs:
            kwargs[arg] = arguments.lookup_default(arguments.Method[method.upper()], arg)
    function_wrapper_partial = functools.partial(
        function_wrapper,
        array_var_context_capsule,
        queue_wrapper.to_capsule(),
        **kwargs
    )

    # WISHLIST: can one use ProcessPoolExecutor somehow on Linux and OSX?
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(loop.run_in_executor(None, function_wrapper_partial))  # type: ignore
    parser = httpstan.callbacks_writer_parser.WriterParser()
    while True:
        try:
            message = queue_wrapper.get_nowait()
        except queue.Empty:
            if future.done():
                break
            await asyncio.sleep(0.1)
            continue
        parsed = parser.parse(message.decode())
        # parsed is None if the message was a blank line or a header with param names
        if parsed:
            yield parsed
    future.result()  # raises exceptions from task, if any
