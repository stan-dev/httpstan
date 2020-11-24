"""Test log_prob endpoint through a Gaussian toy problem."""
import random

import aiohttp
import numpy as np
import pytest

import helpers

program_code = """
parameters {
  real y;
}
model {
  y ~ normal(0, 1);
}
"""

x = random.uniform(0, 10)


def gaussian_lp(x: float, mean: float, var: float) -> float:
    """Analytically evaluate Gaussian log probability."""

    lp = -1 / (2 * var) * (x - mean) ** 2
    return lp


@pytest.mark.parametrize("x", [x])
@pytest.mark.asyncio
async def test_log_prob_analytically(x: float, api_url: str) -> None:
    """Test log probability endpoint."""

    model_name = await helpers.get_model_name(api_url, program_code)
    models_params_url = f"{api_url}/{model_name}/log_prob"
    payload = {"data": {}, "unconstrained_parameters": [x], "adjust_transform": False}
    async with aiohttp.ClientSession() as session:
        async with session.post(models_params_url, json=payload) as resp:
            assert resp.status == 200
            response_payload = await resp.json()
            assert "log_prob" in response_payload
            httpstan_lp = response_payload["log_prob"]
            lp = gaussian_lp(x, 0, 1)
            assert np.allclose(httpstan_lp, lp)


@pytest.mark.asyncio
async def test_log_prob_sampling(api_url: str) -> None:
    """Test log probability endpoint against sampled model."""

    payload = {
        "function": "stan::services::sample::hmc_nuts_diag_e_adapt",
        "data": {},
        "num_samples": 500,
        "num_warmup": 500,
        "random_seed": 1,
    }
    operation = await helpers.sample(api_url, program_code, payload)
    fit_name = operation["result"]["name"]
    fit_bytes_ = await helpers.fit_bytes(api_url, fit_name)
    assert isinstance(fit_bytes_, bytes)
    sample_lp = helpers.extract("lp__", fit_bytes_)[0]
    sample_y = helpers.extract("y", fit_bytes_)[0]
    model_name = await helpers.get_model_name(api_url, program_code)
    models_params_url = f"{api_url}/{model_name}/log_prob"
    payload = {"data": {}, "unconstrained_parameters": [sample_y], "adjust_transform": False}
    async with aiohttp.ClientSession() as session:
        async with session.post(models_params_url, json=payload) as resp:
            assert resp.status == 200
            response_payload = await resp.json()
            assert "log_prob" in response_payload
            httpstan_lp = response_payload["log_prob"]
            assert np.allclose(httpstan_lp, sample_lp)
