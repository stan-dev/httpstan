"""Test sampling."""
import asyncio
import statistics

import requests

import helpers

headers = {"content-type": "application/json"}
program_code = "parameters {real y;} model {y ~ normal(0, 0.0001);}"


def test_fits(httpstan_server):
    """Simple test of sampling."""

    host, port = httpstan_server.host, httpstan_server.port

    async def main():
        models_url = f"http://{host}:{port}/v1/models"
        resp = requests.post(models_url, json={"program_code": program_code})
        assert resp.status_code == 201
        model_name = resp.json()["name"]

        fits_url = f"http://{host}:{port}/v1/models/{model_name.split('/')[-1]}/fits"
        num_samples = num_warmup = 5000
        data = {
            "function": "stan::services::sample::hmc_nuts_diag_e_adapt",
            "num_samples": num_samples,
            "num_warmup": num_warmup,
        }
        resp = requests.post(fits_url, json=data)
        assert resp.status_code == 201
        fit_name = resp.json()["name"]
        assert fit_name is not None

        fit_url = f"http://{host}:{port}/v1/{fit_name}"
        resp = requests.get(fit_url)
        fit_bytes = resp.content
        draws = helpers.extract_draws(fit_bytes, "y")
        assert len(draws) == num_samples, (len(draws), num_samples)
        assert -0.01 < statistics.mean(draws) < 0.01

    asyncio.get_event_loop().run_until_complete(main())


def test_models_actions_bad_args(httpstan_server):
    """Test handler argument handling."""

    host, port = httpstan_server.host, httpstan_server.port

    async def main(loop):
        models_url = f"http://{host}:{port}/v1/models"
        resp = requests.post(models_url, json={"program_code": program_code})
        assert resp.status_code == 201
        model_name = resp.json()["name"]

        fits_url = f"http://{host}:{port}/v1/models/{model_name.split('/')[-1]}/fits"
        resp = requests.post(fits_url, json={"wrong_key": "wrong_value"})
        assert resp.status_code == 422
        assert resp.json() == {"function": ["Missing data for required field."]}

    asyncio.get_event_loop().run_until_complete(main(asyncio.get_event_loop()))
