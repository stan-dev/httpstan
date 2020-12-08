"""Test write_array endpoint through a simple model."""
import random

import aiohttp
import numpy as np
import pytest

import helpers

program_code = """
parameters {
  real x;
  real<lower=0> y;
}
transformed parameters {
    real x_mult = x * 2;
}
generated quantities {
    real z = x + y;
}
"""

x = random.uniform(0, 10)
y = random.uniform(0, 10)


@pytest.mark.parametrize("x", [x])
@pytest.mark.parametrize("y", [y])
@pytest.mark.asyncio
async def test_write_array(x: float, y: float, api_url: str) -> None:
    """Test write array endpoint."""

    model_name = await helpers.get_model_name(api_url, program_code)
    models_params_url = f"{api_url}/{model_name}/write_array"
    payload = {"data": {}, "unconstrained_parameters": [x, y]}
    async with aiohttp.ClientSession() as session:
        async with session.post(models_params_url, json=payload) as resp:
            assert resp.status == 200
            response_payload = await resp.json()
            assert "params_r_constrained" in response_payload
            constrained_params = response_payload["params_r_constrained"]
            assert np.allclose(x, constrained_params[0])
            assert np.allclose(np.exp(y), constrained_params[1])
            assert np.allclose(x * 2, constrained_params[2])
            assert np.allclose(x + np.exp(y), constrained_params[3])
