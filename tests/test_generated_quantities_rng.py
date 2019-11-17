"""Test generated quantities rng."""
import typing

import numpy as np
import pytest

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


@pytest.mark.asyncio
async def test_generated_quantities_rng(api_url: str) -> None:
    """Test consistency in rng in `generated quantities` block."""

    async def draws(random_seed: int) -> typing.List[typing.Union[int, float]]:
        param_name = "y"
        payload = {
            "function": "stan::services::sample::hmc_nuts_diag_e_adapt",
            "random_seed": random_seed,
        }
        return await helpers.sample_then_extract(api_url, program_code, payload, param_name)

    draws1 = np.array(await draws(random_seed=1))
    draws2 = np.array(await draws(random_seed=1))
    draws3 = np.array(await draws(random_seed=2))
    assert len(draws1) == len(draws2) == len(draws3)
    assert len(draws1) >= 1000
    assert np.allclose(draws1, draws2)
    assert not np.allclose(draws1, draws3)
