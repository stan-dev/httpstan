"""Test consistency in rng in `transformed data` block."""
import typing

import aiohttp
import numpy as np
import pytest

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

data = {"N": 3}


@pytest.mark.asyncio
async def test_transformed_data_params(api_url: str) -> None:
    """Test getting parameters."""

    model_name = await helpers.get_model_name(api_url, program_code)
    models_params_url = f"{api_url}/{model_name}/params"
    payload = {"data": data}
    async with aiohttp.ClientSession() as session:
        async with session.post(models_params_url, json=payload) as resp:
            assert resp.status == 200
            response_payload = await resp.json()
            assert "name" in response_payload and response_payload["name"] == model_name
            assert "params" in response_payload and len(response_payload["params"])
            params = response_payload["params"]
            param = params[0]
            assert param["name"] == "mu"
            assert param["dims"] == []
            assert param["constrained_names"] == ["mu"]


@pytest.mark.asyncio
async def test_transformed_data_rng(api_url: str) -> None:
    """Test consistency in rng in `transformed data` block."""

    async def draws(random_seed: int) -> typing.List[typing.Union[int, float]]:
        param_name = "mean_y"
        payload = {
            "function": "stan::services::sample::hmc_nuts_diag_e_adapt",
            "data": data,
            "random_seed": random_seed,
        }
        return await helpers.sample_then_extract(api_url, program_code, payload, param_name)

    draws1 = np.array(await draws(random_seed=123))
    draws2 = np.array(await draws(random_seed=123))
    draws3 = np.array(await draws(random_seed=456))
    assert len(draws1) == len(draws2) == len(draws3)
    assert len(draws1) >= 1000
    # look at the first draw
    assert draws1[0] == draws2[0] != draws3[0]
    # look at all draws
    assert np.allclose(draws1, draws2)
    assert not np.allclose(draws1, draws3)
