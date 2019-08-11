"""Test generated quantities rng."""
import asyncio
import requests
import typing

import numpy as np

import helpers


program_code = """
    parameters {
      real z;
    }
    model {
      z ~ normal(0, 1);
    }
    generated quantities {
      real y = normal_rng(0, 1);
    }
"""


def test_generated_quantities_rng(api_url: str) -> None:
    """Test consistency in rng in `generated quantities` block."""

    async def draws(random_seed: int) -> typing.List[typing.Union[int, float]]:
        model_name = helpers.get_model_name(api_url, program_code)
        fits_url = f"{api_url}/models/{model_name.split('/')[-1]}/fits"
        data = {
            "function": "stan::services::sample::hmc_nuts_diag_e_adapt",
            "random_seed": random_seed,
        }
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
        fit_bytes = resp.content
        return helpers.extract_draws(fit_bytes, "y")

    async def main() -> None:
        draws1 = np.array(await draws(random_seed=1))
        draws2 = np.array(await draws(random_seed=1))
        draws3 = np.array(await draws(random_seed=2))
        assert len(draws1) == len(draws2) == len(draws3)
        assert len(draws1) >= 1000
        assert np.allclose(draws1, draws2)
        assert not np.allclose(draws1, draws3)

    asyncio.get_event_loop().run_until_complete(main())
