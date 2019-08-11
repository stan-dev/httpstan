"""Test consistency in rng in `transformed data` block."""
import asyncio
import typing

import numpy as np
import requests

import helpers

program_code = """
    data {
      int<lower=0> N;
    }
    transformed data {
      vector[N] y;
      for (n in 1:N)
        y[n] = normal_rng(0, 1);
    }
    parameters {
      real mu;
      real<lower = 0> sigma;
    }
    model {
      y ~ normal(mu, sigma);
    }
    generated quantities {
      real mean_y = mean(y);
      real sd_y = sd(y);
    }
"""

test_data = {"N": 3}


def test_transformed_data_params(api_url: str) -> None:
    """Test getting parameters."""

    async def main() -> None:
        model_name = helpers.get_model_name(api_url, program_code)
        models_params_url = f"{api_url}/models/{model_name.split('/')[-1]}/params"
        resp = requests.post(models_params_url, json={"data": test_data})
        assert resp.status_code == 200
        response_payload = resp.json()
        assert "name" in response_payload and response_payload["name"] == model_name
        assert "params" in response_payload and len(response_payload["params"])
        params = response_payload["params"]
        param = params[0]
        assert param["name"] == "mu"
        assert param["dims"] == []
        assert param["constrained_names"] == ["mu"]

    asyncio.get_event_loop().run_until_complete(main())


def test_transformed_data_rng(api_url: str) -> None:
    """Test consistency in rng in `transformed data` block."""

    async def draws(random_seed: typing.Optional[int] = None) -> typing.List[typing.Union[int, float]]:
        model_name = helpers.get_model_name(api_url, program_code)
        fits_url = f"{api_url}/models/{model_name.split('/')[-1]}/fits"
        data: dict = {"function": "stan::services::sample::hmc_nuts_diag_e_adapt", "data": test_data}
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
        return helpers.extract_draws(fit_bytes, "mean_y")

    async def main() -> None:
        draws1 = np.array(await draws(random_seed=123))
        draws2 = np.array(await draws(random_seed=123))
        draws3 = np.array(await draws(random_seed=456))
        draws4 = np.array(await draws())
        assert len(draws1) == len(draws2) == len(draws3)
        assert len(draws1) >= 1000
        # look at the first draw
        assert draws1[0] == draws2[0] != draws4[0]
        assert draws2[0] != draws4[0]
        assert draws1[0] != draws3[0] != draws4[0]
        # look at all draws
        assert np.allclose(draws1, draws2)
        assert not np.allclose(draws1, draws3)

    asyncio.get_event_loop().run_until_complete(main())
