"""Superficial test of `generated quantities` block."""
import asyncio

import numpy as np
import requests

import helpers

program_code = """
    parameters {
      real y;
    }
    model {
      y ~ normal(0, 1);
    }
    generated quantities {
        real y_new = y + 3;
    }
"""


def test_generated_quantities_block(api_url: str) -> None:
    """Test `generated_quantities` block."""

    async def main() -> None:
        model_name = helpers.get_model_name(api_url, program_code)
        fits_url = f"{api_url}/models/{model_name.split('/')[-1]}/fits"
        data = {"function": "stan::services::sample::hmc_nuts_diag_e_adapt"}
        resp = requests.post(fits_url, json=data)
        assert resp.status_code == 201
        operation = resp.json()
        operation_name = operation["name"]

        fit_name = operation["metadata"]["fit"]["name"]
        resp = requests.get(f"{api_url}/{operation_name}")

        # wait until fit is finished
        while not requests.get(f"{api_url}/{operation_name}").json()["done"]:
            await asyncio.sleep(0.1)

        fit_url = f"{api_url}/{fit_name}"
        resp = requests.get(fit_url)
        fit_bytes = resp.content
        y = np.array(helpers.extract_draws(fit_bytes, "y"))
        y_new = np.array(helpers.extract_draws(fit_bytes, "y_new"))
        np.testing.assert_allclose(y + 3, y_new, atol=0.001)

    asyncio.get_event_loop().run_until_complete(main())
