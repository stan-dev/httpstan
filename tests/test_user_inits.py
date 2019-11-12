"""Test user-provided initial values for parameters."""
import random
import statistics

import aiohttp
import pytest

import helpers

program_code = """
    data {
      real x;
    }
    parameters {
      real mu;
    }
    model {
      x ~ normal(mu,1);
    }
"""
data = {"x": 2}


@pytest.mark.asyncio
async def test_user_inits(api_url: str) -> None:
    """Test that user-provided initial values make some difference."""

    random_seed = random.randrange(2 ** 16) + 1
    sample_kwargs = {
        "function": "stan::services::sample::hmc_nuts_diag_e_adapt",
        "data": data,
        "num_samples": 10,
        "num_warmup": 0,
        "random_seed": random_seed,
    }
    param_name = "mu"
    draws1 = await helpers.sample_then_extract(api_url, program_code, sample_kwargs, param_name)
    assert draws1 is not None

    sample_kwargs = {
        "function": "stan::services::sample::hmc_nuts_diag_e_adapt",
        "data": data,
        "num_samples": 10,
        "num_warmup": 0,
        "random_seed": random_seed,
        "init": {"mu": 400},
    }
    param_name = "mu"
    draws2 = await helpers.sample_then_extract(api_url, program_code, sample_kwargs, param_name)
    assert draws2 is not None
    assert statistics.mean(draws1) != statistics.mean(draws2)

    sample_kwargs = {
        "function": "stan::services::sample::hmc_nuts_diag_e_adapt",
        "data": data,
        "num_samples": 10,
        "num_warmup": 0,
        "random_seed": random_seed,
        "init": {"mu": 4000},
    }
    param_name = "mu"
    draws3 = await helpers.sample_then_extract(api_url, program_code, sample_kwargs, param_name)
    assert draws3 is not None
    assert statistics.mean(draws3) != statistics.mean(draws2)


@pytest.mark.asyncio
async def test_user_inits_invalid_value(api_url: str) -> None:
    """Test providing an invalid `init` (e.g., a number)."""

    sample_kwargs = {
        "function": "stan::services::sample::hmc_nuts_diag_e_adapt",
        "data": data,
        "num_samples": 10,
        "num_warmup": 0,
        "init": -3,
    }
    model_name = await helpers.get_model_name(api_url, program_code)
    payload = sample_kwargs
    payload.update(**sample_kwargs)
    fits_url = f"{api_url}/{model_name}/fits"
    async with aiohttp.ClientSession() as session:
        async with session.post(fits_url, json=payload) as resp:
            assert resp.status == 422
            response_payload = await resp.json()
    assert response_payload.get("init")
    assert response_payload["init"]["_schema"].pop() == "Invalid input type."
