"""Test debug mode."""
import pytest

import httpstan.config

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
async def test_debug_mode(api_url: str) -> None:
    """Test that sampling does not crash in debug mode."""

    assert not httpstan.config.HTTPSTAN_DEBUG
    httpstan.config.HTTPSTAN_DEBUG = True
    assert httpstan.config.HTTPSTAN_DEBUG

    sample_kwargs = {
        "function": "stan::services::sample::hmc_nuts_diag_e_adapt",
        "data": data,
        "num_samples": 10,
        "num_warmup": 0,
    }
    param_name = "mu"
    draws1 = await helpers.sample_then_extract(api_url, program_code, sample_kwargs, param_name)
    assert draws1 is not None
