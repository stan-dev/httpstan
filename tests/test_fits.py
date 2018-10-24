"""Test sampling."""
import asyncio
import json
import statistics

import aiohttp

import helpers

headers = {"content-type": "application/json"}
program_code = "parameters {real y;} model {y ~ normal(0, 0.0001);}"


def test_fits(httpstan_server):
    """Simple test of sampling."""

    host, port = httpstan_server.host, httpstan_server.port

    async def main():
        async with aiohttp.ClientSession() as session:
            models_url = "http://{}:{}/v1/models".format(host, port)
            data = {"program_code": program_code}
            async with session.post(models_url, data=json.dumps(data), headers=headers) as resp:
                assert resp.status == 201
                model_name = (await resp.json())["name"]

            fits_url = f"http://{host}:{port}/v1/models/{model_name.split('/')[-1]}/fits"
            num_samples = num_warmup = 5000
            data = {
                "function": "stan::services::sample::hmc_nuts_diag_e_adapt",
                "num_samples": num_samples,
                "num_warmup": num_warmup,
            }
            async with session.post(fits_url, data=json.dumps(data), headers=headers) as resp:
                assert resp.status == 201, await resp.text()
                fit_name = (await resp.json())["name"]
                assert fit_name is not None

            fit_url = f"http://{host}:{port}/v1/{fit_name}"
            async with session.get(fit_url, headers=headers) as resp:
                fit_bytes = await resp.read()
                draws = helpers.extract_draws(fit_bytes, "y")
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
                assert resp.status == 201
                model_name = (await resp.json())["name"]

            fits_url = f"http://{host}:{port}/v1/models/{model_name.split('/')[-1]}/fits"
            data = {"wrong_key": "wrong_value"}
            async with session.post(
                fits_url, data=json.dumps(data), headers=headers
            ) as resp:
                assert resp.status == 422
                assert await resp.json() == {"function": ["Missing data for required field."]}

    asyncio.get_event_loop().run_until_complete(main(asyncio.get_event_loop()))
