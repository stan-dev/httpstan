"""Call and process output of stan::services functions.

Functions here perform the menial task of calling (from Python) a named C++
function in stan::services given a specific Stan Program. The output of the
stan::services function is routed from stan::callbacks writers into Python via a
queue. The queue is a lock-free single-producer/single-consumer queue defined in
<boost/lockfree/spsc_queue.hpp>.
"""
import asyncio
import json
import queue  # for queue.Empty exception

import httpstan.spsc_queue
import httpstan.stan


class StanMessageParser:
    """Parse raw Stan writer output into JSON-serializeable Python dict.

    This is a bit of a state machine since Stan only tells us the names
    of the parameters being sampled before the first sample.

    With luck, the writer callbacks in stan::services will eventually provide
    directly the context which this class recovers. At this point, this class
    may be removed.

    """

    def __init__(self):  # noqa
        self.sample_fields, self.diagnostic_fields = None, None

    def __call__(self, message):  # noqa
        writer_name, body = (val.strip() for val in message.split(':', 1))
        if not body:
            # ignore blank lines
            return
        try:
            values = json.loads(body)
        except json.decoder.JSONDecodeError:
            return {'message': {'writer': writer_name, 'values': [body]}}

        if self.sample_fields is None and writer_name == 'sample_writer':
            self.sample_fields = values
            return
        if self.diagnostic_fields is None and writer_name == 'diagnostic_writer':
            self.diagnostic_fields = values
            return

        if writer_name in {'sample_writer', 'diagnostic_writer'}:
            assert self.sample_fields is not None, (self.sample_fields, message)
            assert self.diagnostic_fields is not None, (self.diagnostic_fields, message)
            fields = self.sample_fields if writer_name == 'sample_writer' else self.diagnostic_fields
            try:
                payload = {'message': {'values': dict(zip(fields, values))}}
            except TypeError:
                # in adapt mode, sample_writers outputs single double
                payload = {'message': {'values': values}}
        else:
            payload = {'message': {'values': values}}
        payload['message']['writer'] = writer_name
        return payload


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
    parser = StanMessageParser()
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
        parsed = parser(message.decode())
        # parsed is None if the message was a blank line or a csv header
        if parsed:
            yield parsed
    future.result()  # raises exceptions from task, if any
