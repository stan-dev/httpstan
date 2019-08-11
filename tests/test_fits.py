"""Test sampling."""
import asyncio
import statistics
import typing

import numpy as np
import requests

import helpers

headers = {"content-type": "application/json"}
program_code = "parameters {real y;} model {y ~ normal(0, 0.0001);}"


def test_fits(api_url: str) -> None:
    """Simple test of sampling."""

    async def main() -> None:
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
        assert resp.status_code == 200
        fit_bytes = resp.content
        draws = helpers.extract_draws(fit_bytes, "y")
        assert len(draws) == num_samples, (len(draws), num_samples)
        assert -0.01 < statistics.mean(draws) < 0.01

    asyncio.get_event_loop().run_until_complete(main())


def test_models_actions_bad_args(api_url: str) -> None:
    """Test handler argument handling."""

    async def main() -> None:
        model_name = helpers.get_model_name(api_url, program_code)
        fits_url = f"{api_url}/models/{model_name.split('/')[-1]}/fits"
        resp = requests.post(fits_url, json={"wrong_key": "wrong_value"})
        assert resp.status_code == 422
        assert resp.json() == {"function": ["Missing data for required field."]}

    asyncio.get_event_loop().run_until_complete(main())


def test_fits_random_seed(api_url: str) -> None:
    """Simple test of sampling with fixed random seed."""

    async def draws(
        random_seed: typing.Optional[int] = None
    ) -> typing.List[typing.Union[int, float]]:
        model_name = helpers.get_model_name(api_url, program_code)
        fits_url = f"{api_url}/models/{model_name.split('/')[-1]}/fits"
        data: dict = {"function": "stan::services::sample::hmc_nuts_diag_e_adapt"}
        if random_seed is not None:
            data["random_seed"] = random_seed
        resp = requests.post(fits_url, json=data)
        assert resp.status_code == 201
        operation = resp.json()
        operation_name = operation["name"]
        fit_name = operation["metadata"]["fit"]["name"]

        resp = requests.get(f"{api_url}/{operation_name}")
        assert resp.status_code == 200, f"{api_url}/{operation_name}"

        # wait until fit is finished
        while not requests.get(f"{api_url}/{operation_name}").json()["done"]:
            await asyncio.sleep(0.1)

        fit_url = f"{api_url}/{fit_name}"
        resp = requests.get(fit_url)
        assert resp.status_code == 200
        fit_bytes = resp.content
        return helpers.extract_draws(fit_bytes, "y")

    async def main() -> None:
        draws1 = np.array(await draws(random_seed=123))
        draws2 = np.array(await draws(random_seed=123))
        draws3 = np.array(await draws(random_seed=456))
        draws4 = np.array(await draws())

        assert draws1[0] == draws2[0] != draws4[0]
        assert draws2[0] != draws4[0]
        assert draws1[0] != draws3[0] != draws4[0]
        # look at all draws
        assert np.allclose(draws1, draws2)
        assert not np.allclose(draws1, draws3)

    asyncio.get_event_loop().run_until_complete(main())
