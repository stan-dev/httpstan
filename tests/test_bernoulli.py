"""Test sampling from Bernoulli model."""
import asyncio
import json
import time

import aiohttp
import functools
import requests


host, port = '127.0.0.1', 8080
programs_url = 'http://{}:{}/v1/programs'.format(host, port)
headers = {'content-type': 'application/json'}
program_code = """
    data {
        int<lower=0> N;
        int<lower=0,upper=1> y[N];
    }
    parameters {
        real<lower=0,upper=1> theta;
    }
    model {
        theta ~ beta(1,1);
        for (n in 1:N)
        y[n] ~ bernoulli(theta);
    }
    """
data = {'N': 10, 'y': (0, 1, 0, 0, 0, 0, 0, 0, 0, 1)}


async def validate_samples(resp):
    """Superficially validate samples from Stan Program."""
    assert resp.status == 200
    while True:
        chunk = await resp.content.readline()
        if not chunk:
            break
        assert len(chunk)
        assert len(json.loads(chunk)) > 0
    return True


def test_bernoulli(loop_with_server):
    """Test sampling from Bernoulli program with defaults."""
    async def main(loop):
        async with aiohttp.ClientSession() as session:
            payload = {'program_code': program_code}
            async with session.post(programs_url, data=json.dumps(payload), headers=headers) as resp:
                assert resp.status == 200
                program_id = (await resp.json())['program']['id']

            programs_actions_url = 'http://{}:{}/v1/programs/{}/actions'.format(host, port, program_id)
            payload = {'type': 'hmc_nuts_diag_e_adapt', 'data': data}
            async with session.post(programs_actions_url, data=json.dumps(payload), headers=headers) as resp:
                await validate_samples(resp)

    loop_with_server.run_until_complete(main(loop_with_server))


def test_bernoulli_parallel(loop_with_server):
    """Test sampling from Bernoulli program in parallel."""
    async def main(loop):
        async with aiohttp.ClientSession() as session:
            payload = {'program_code': program_code}
            async with session.post(programs_url, data=json.dumps(payload), headers=headers) as resp:
                assert resp.status == 200
                program_id = (await resp.json())['program']['id']

        programs_actions_url = 'http://{}:{}/v1/programs/{}/actions'.format(host, port, program_id)
        payload = {'type': 'hmc_nuts_diag_e_adapt', 'data': data}

        # record time for sampling
        # this must be run in an executor because loop is managing the server
        request_function = functools.partial(requests.post, programs_actions_url, json=payload)
        t0 = time.time()
        r = await loop.run_in_executor(None, request_function)
        elapsed = time.time() - t0

        # run many requests in parallel
        num_threads = 4
        t0 = time.time()
        futs = [asyncio.ensure_future(loop.run_in_executor(None, request_function)) for _ in range(num_threads)]
        for fut in futs:
            r = await fut
            assert r.text
        assert (time.time() - t0) < num_threads * elapsed

    loop_with_server.run_until_complete(main(loop_with_server))
