"""Test sampling from Bernoulli model."""
import asyncio
import json

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


def test_bernoulli(loop_with_server, host, port):
    """Test sampling from Bernoulli model with defaults."""

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

    loop_with_server.run_until_complete(main())


def test_bernoulli_params(loop_with_server, host, port):
    """Test getting parameters from Bernoulli model."""

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

    loop_with_server.run_until_complete(main())


def test_bernoulli_parallel(loop_with_server, host, port):
    """Test sampling from Bernoulli model with defaults, in parallel."""

    async def main():
        models_url = "http://{}:{}/v1/models".format(host, port)
        payload = {"program_code": program_code}
        async with aiohttp.ClientSession() as session:
            async with session.post(models_url, data=json.dumps(payload), headers=headers) as resp:
                assert resp.status == 200
                model_id = (await resp.json())["id"]

        models_actions_url = "http://{}:{}/v1/models/{}/actions".format(host, port, model_id)
        payload = {"type": "stan::services::sample::hmc_nuts_diag_e_adapt", "data": data}

        # launch many samplers
        num_samplers = 8
        try:
            sessions = [aiohttp.ClientSession() for _ in range(num_samplers)]
            responses = [
                await session.post(models_actions_url, data=json.dumps(payload), headers=headers)
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
            for session in sessions:
                await session.close()

    loop_with_server.run_until_complete(main())
