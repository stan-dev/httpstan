"""Test sampling."""
import asyncio
import statistics

import requests

import helpers

headers = {"content-type": "application/json"}
program_code = "parameters {real y;} model {y ~ normal(0, 0.0001);}"


def test_fits(api_url):
    """Simple test of sampling."""

    async def main():
        model_name = helpers.get_model_name(api_url, program_code)
        fits_url = f"{api_url}/models/{model_name.split('/')[-1]}/fits"
        num_samples = num_warmup = 5000
        data = {
            "function": "stan::services::sample::hmc_nuts_diag_e_adapt",
            "num_samples": num_samples,
            "num_warmup": num_warmup,
        }
        resp = requests.post(fits_url, json=data)
        assert resp.status_code == 201
        operation = resp.json()
        operation_name = operation["name"]
        assert operation_name is not None
        assert operation_name.startswith("operations/")
        assert not operation["done"]

        fit_name = operation["metadata"]["fit"]["name"]

        resp = requests.get(f"{api_url}/{operation_name}")
        assert resp.status_code == 200, f"{api_url}/{operation_name}"
        assert not resp.json()["done"], resp.json()

        # wait until fit is finished
        while not requests.get(f"{api_url}/{operation_name}").json()["done"]:
            await asyncio.sleep(0.1)

        fit_url = f"{api_url}/{fit_name}"
        resp = requests.get(fit_url)
        fit_bytes = resp.content
        draws = helpers.extract_draws(fit_bytes, "y")
        assert len(draws) == num_samples, (len(draws), num_samples)
        assert -0.01 < statistics.mean(draws) < 0.01

    asyncio.get_event_loop().run_until_complete(main())


def test_models_actions_bad_args(api_url):
    """Test handler argument handling."""

    async def main(loop):
        model_name = helpers.get_model_name(api_url, program_code)
        fits_url = f"{api_url}/models/{model_name.split('/')[-1]}/fits"
        resp = requests.post(fits_url, json={"wrong_key": "wrong_value"})
        assert resp.status_code == 422
        assert resp.json() == {"function": ["Missing data for required field."]}

    asyncio.get_event_loop().run_until_complete(main(asyncio.get_event_loop()))