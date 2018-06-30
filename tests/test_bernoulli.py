"""Test sampling from Bernoulli model."""
import asyncio
import json
import multiprocessing
import time

import aiohttp

headers = {"content-type": "application/json"}
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
data = {"N": 10, "y": (0, 1, 0, 0, 0, 0, 0, 0, 0, 1)}


async def validate_samples(resp):
    """Superficially validate samples from a Stan model."""
    assert resp.status == 200
    while True:
        chunk = await resp.content.readline()
        if not chunk:
            break
        assert len(chunk)
        assert len(json.loads(chunk)) > 0
    return True


def test_bernoulli(httpstan_server):
    """Test sampling from Bernoulli model with defaults."""
    host, port = httpstan_server.host, httpstan_server.port

    async def main():
        models_url = "http://{}:{}/v1/models".format(host, port)
        payload = {"program_code": program_code}
        async with aiohttp.ClientSession() as session:
            async with session.post(models_url, data=json.dumps(payload), headers=headers) as resp:
                assert resp.status == 200
                model_id = (await resp.json())["id"]

        models_actions_url = "http://{}:{}/v1/models/{}/actions".format(host, port, model_id)
        payload = {"type": "stan::services::sample::hmc_nuts_diag_e_adapt", "data": data}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                models_actions_url, data=json.dumps(payload), headers=headers
            ) as resp:
                await validate_samples(resp)

    asyncio.get_event_loop().run_until_complete(main())


def test_bernoulli_params(httpstan_server):
    """Test getting parameters from Bernoulli model."""

    host, port = httpstan_server.host, httpstan_server.port

    async def main():
        async with aiohttp.ClientSession() as session:
            models_url = "http://{}:{}/v1/models".format(host, port)
            payload = {"program_code": program_code}
            async with session.post(models_url, data=json.dumps(payload), headers=headers) as resp:
                assert resp.status == 200
                model_id = (await resp.json())["id"]

            models_params_url = "http://{}:{}/v1/models/{}/params".format(host, port, model_id)
            payload = {"data": data}
            async with session.post(
                models_params_url, data=json.dumps(payload), headers=headers
            ) as resp:
                assert resp.status == 200
                response_payload = await resp.json()
                assert "id" in response_payload and response_payload["id"] == model_id
                assert "params" in response_payload and len(response_payload["params"])
                params = response_payload["params"]
                param = params[0]
                assert param["name"] == "theta"
                assert param["dims"] == []
                assert param["constrained_names"] == ["theta"]

    asyncio.get_event_loop().run_until_complete(main())


def test_bernoulli_parallel(httpstan_server):
    """Test sampling from Bernoulli model with defaults, in parallel."""

    host, port = httpstan_server.host, httpstan_server.port

    async def main():
        models_url = "http://{}:{}/v1/models".format(host, port)
        payload = {"program_code": program_code}
        async with aiohttp.ClientSession() as session:
            async with session.post(models_url, data=json.dumps(payload), headers=headers) as resp:
                assert resp.status == 200
                model_id = (await resp.json())["id"]

        models_actions_url = "http://{}:{}/v1/models/{}/actions".format(host, port, model_id)
        # draw enough samples that sampling itself takes some time, use a high
        # warmup count because it will not generate draws which will require CPU
        # time to serialize and send.
        num_warmup = 500_000
        num_samples = 100
        payload = {
            "type": "stan::services::sample::hmc_nuts_diag_e_adapt",
            "data": data,
            "num_warmup": num_warmup,
            "num_samples": num_samples,
        }

        t0 = time.time()
        # draw samples once serially to get a baseline time measurement
        async with aiohttp.ClientSession() as session:
            async with session.post(
                models_actions_url, data=json.dumps(payload), headers=headers
            ) as response:
                await validate_samples(response)
        elapsed = time.time() - t0

        # launch many samplers in parallel
        t0 = time.time()
        num_parallel = 2
        try:
            sessions = [aiohttp.ClientSession() for _ in range(num_parallel)]
            try:
                responses = [
                    await session.post(
                        models_actions_url, data=json.dumps(payload), headers=headers
                    )
                    for session in sessions
                ]
                # validate samples in reverse order, making sure that no blocking is happening
                await asyncio.gather(
                    *[
                        asyncio.ensure_future(validate_samples(response))
                        for response in reversed(responses)
                    ]
                )
            finally:
                for response in responses:
                    response.close()  # ClientResponse.close is not a coroutine
        finally:
            for session in sessions:
                await session.close()
        elapsed_parallel = time.time() - t0
        # sampling two chains in parallel should not take much longer than sampling
        # one chain, assuming that the system has at least two cores.
        overhead = 1.6
        if multiprocessing.cpu_count() > 1:
            assert elapsed_parallel < elapsed * overhead
        else:
            assert elapsed_parallel < elapsed * num_parallel * overhead

    asyncio.get_event_loop().run_until_complete(main())
