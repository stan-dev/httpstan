"""Call and process output of stan::services functions.

Functions here perform the menial task of calling (from Python) a named C++
function in stan::services given a specific Stan Program. The output of the
stan::services function is routed from stan::callbacks writers into Python via a
queue. The queue is a lock-free single-producer/single-consumer queue defined in
<boost/lockfree/spsc_queue.hpp>.
"""
import asyncio
import queue  # for queue.Empty exception

import httpstan.callbacks_writer_parser
import httpstan.spsc_queue
import httpstan.stan


async def call_sample(function_name: str, program_module, data: dict,
                      random_seed: int, chain: int, init_radius: float,
                      num_samples: int, num_warmup: int):
    """Call stan::services function.

    Yields (asynchronously) messages from the stan::callbacks writers which are
    written to by the stan::services function.

    This is a coroutine function.

    Arguments:
        function_name: name of function in stan::services
        program_module (module): Stan Program extension module
        data: dictionary with data with which to populate array_var_context
        random_seed: stan::services function argument, see C++ documentation.
        chain: stan::services function argument, see C++ documentation.
        init_radius: stan::services function argument, see C++ documentation.
        num_samples: stan::services function argument, see C++ documentation.
        num_warmup: stan::services function argument, see C++ documentation.

    """
    queue_wrapper = httpstan.spsc_queue.SPSCQueue(capacity=10000)
    array_var_context_capsule = httpstan.stan.make_array_var_context(data)

    function_wrapper = getattr(program_module, function_name + '_wrapper')
    function_args = (array_var_context_capsule, queue_wrapper.to_capsule(),
                     random_seed, chain, init_radius, num_warmup, num_samples)
    parser = httpstan.callbacks_writer_parser.WriterParser()
    # WISHLIST: can one use ProcessPoolExecutor somehow on Linux and OSX?
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(loop.run_in_executor(None, function_wrapper, *function_args))
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
