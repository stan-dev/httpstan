"""Test sampling from Bernoulli model."""
import asyncio
import json
import time

import aiohttp
import functools
import requests


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


def test_bernoulli(loop_with_server, host, port):
    """Test sampling from Bernoulli program with defaults."""
    async def main():
        async with aiohttp.ClientSession() as session:
            programs_url = 'http://{}:{}/v1/programs'.format(host, port)
            payload = {'program_code': program_code}
            async with session.post(programs_url, data=json.dumps(payload), headers=headers) as resp:
                assert resp.status == 200
                program_id = (await resp.json())['id']

            programs_actions_url = 'http://{}:{}/v1/programs/{}/actions'.format(host, port, program_id)
            payload = {'type': 'stan::services::sample::hmc_nuts_diag_e_adapt', 'data': data}
            async with session.post(programs_actions_url, data=json.dumps(payload), headers=headers) as resp:
                await validate_samples(resp)

    loop_with_server.run_until_complete(main())
