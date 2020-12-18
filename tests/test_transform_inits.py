"""Test transform_inits endpoint through a simple model."""
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
async def test_transform_inits(x: float, y: float, api_url: str) -> None:
    """Test transform inits endpoint."""
    model_name = await helpers.get_model_name(api_url, program_code)
    write_array_url = f"{api_url}/{model_name}/write_array"
    write_payload = {"data": {}, "unconstrained_parameters": [x, y]}
    async with aiohttp.ClientSession() as session:
        async with session.post(write_array_url, json=write_payload) as resp:
            assert resp.status == 200
            response_payload = await resp.json()
            assert "params_r_constrained" in response_payload
            constrained_params = response_payload["params_r_constrained"]
    constrained_pars = {
        "x": constrained_params[0],
        "y": constrained_params[1],
        "x_mult": constrained_params[2],
        "z": constrained_params[3],
    }
    transform_inits_url = f"{api_url}/{model_name}/transform_inits"
    transform_payload = {
        "data": {},
        "constrained_parameters": constrained_pars,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(transform_inits_url, json=transform_payload) as resp:
            assert resp.status == 200
            response_payload = await resp.json()
            assert "params_r_unconstrained" in response_payload
            unconstrained_params = response_payload["params_r_unconstrained"]
            assert np.allclose([x, y], unconstrained_params)
