"""Test sampling from Eight Schools model."""
import typing

import aiohttp
import pytest

import helpers


program_code = """
    data {
      int<lower=0> J; // number of schools
      real y[J]; // estimated treatment effects
      real<lower=0> sigma[J]; // s.e. of effect estimates
    }
    parameters {
      real mu;
      real<lower=0> tau;
      real eta[J];
    }
    transformed parameters {
      real theta[J];
      for (j in 1:J)
        theta[j] = mu + tau * eta[j];
    }
    model {
      target += normal_lpdf(eta | 0, 1);
      target += normal_lpdf(y | theta, sigma);
    }
"""
schools_data = {
    "J": 8,
    "y": (28, 8, -3, 7, -1, 1, 18, 12),
    "sigma": (15, 10, 16, 11, 9, 11, 10, 18),
}


@pytest.mark.asyncio
async def test_eight_schools(api_url: str) -> None:
    """Test sampling from Eight Schools model with defaults."""
    payload = {
        "function": "stan::services::sample::hmc_nuts_diag_e_adapt",
        "data": schools_data,
    }
    param_name = "mu"
    mu = await helpers.sample_then_extract(api_url, program_code, payload, param_name)
    assert len(mu) == 1_000


@pytest.mark.asyncio
async def test_eight_schools_params(api_url: str) -> None:
    """Test getting parameters from Eight Schools model."""

    model_name = await helpers.get_model_name(api_url, program_code)
    models_params_url = f"{api_url}/{model_name}/params"
    payload = {"data": schools_data}
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
            param = params[1]
            assert param["name"] == "tau"
            assert param["dims"] == []
            assert param["constrained_names"] == ["tau"]
            param = params[2]
            assert param["name"] == "eta"
            assert param["dims"] == [schools_data["J"]]
            assert param["constrained_names"] == [
                f"eta.{i}" for i in range(1, typing.cast(int, schools_data["J"]) + 1)
            ]
