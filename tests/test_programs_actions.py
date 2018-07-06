"""Test sampling."""
import asyncio
import json
import statistics

import aiohttp

import helpers

headers = {"content-type": "application/json"}
program_code = "parameters {real y;} model {y ~ normal(0, 0.0001);}"


def test_models_actions(httpstan_server):
    """Simple test of sampling."""

    host, port = httpstan_server.host, httpstan_server.port

    async def main():
        async with aiohttp.ClientSession() as session:
            models_url = "http://{}:{}/v1/models".format(host, port)
            data = {"program_code": program_code}
            async with session.post(models_url, data=json.dumps(data), headers=headers) as resp:
                assert resp.status == 200
                model_id = (await resp.json())["id"]

            models_actions_url = "http://{}:{}/v1/models/{}/actions".format(host, port, model_id)
            num_samples = num_warmup = 5000
            data = {
                "type": "stan::services::sample::hmc_nuts_diag_e_adapt",
                "num_samples": num_samples,
                "num_warmup": num_warmup,
            }
            async with session.post(
                models_actions_url, data=json.dumps(data), headers=headers
            ) as resp:
                draws = await helpers.extract_draws(resp, "y")
            assert len(draws) == num_samples, (len(draws), num_samples)
            assert -0.01 < statistics.mean(draws) < 0.01

    asyncio.get_event_loop().run_until_complete(main())


def test_models_actions_bad_args(httpstan_server):
    """Test handler argument handling."""

    host, port = httpstan_server.host, httpstan_server.port

    async def main(loop):
        async with aiohttp.ClientSession() as session:
            data = {"program_code": program_code}
            models_url = "http://{}:{}/v1/models".format(host, port)
            async with session.post(models_url, data=json.dumps(data), headers=headers) as resp:
                assert resp.status == 200
                model_id = (await resp.json())["id"]

            models_actions_url = "http://{}:{}/v1/models/{}/actions".format(host, port, model_id)
            data = {"wrong_key": "wrong_value"}
            async with session.post(
                models_actions_url, data=json.dumps(data), headers=headers
            ) as resp:
                assert resp.status == 422
                assert await resp.json() == {"type": ["Missing data for required field."]}

    asyncio.get_event_loop().run_until_complete(main(asyncio.get_event_loop()))
