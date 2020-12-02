"""Test log_prob endpoint through a Gaussian toy problem."""
import random
from typing import List

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


def gaussian_gradient(x: float, mean: float, var: float) -> List[float]:
    """Analytically evaluate Gaussian gradient."""
    gradient = (mean - x) / (var ** 2)
    return [gradient]


@pytest.mark.parametrize("x", [x])
@pytest.mark.asyncio
async def test_log_prob_grad_analytically(x: float, api_url: str) -> None:
    """Test log_prob_grad endpoint."""

    model_name = await helpers.get_model_name(api_url, program_code)
    models_params_url = f"{api_url}/{model_name}/log_prob_grad"
    payload = {"data": {}, "unconstrained_parameters": [x], "adjust_transform": False}
    async with aiohttp.ClientSession() as session:
        async with session.post(models_params_url, json=payload) as resp:
            assert resp.status == 200
            response_payload = await resp.json()
            assert "log_prob_grad" in response_payload
            httpstan_grad = response_payload["log_prob_grad"]
            gradient = gaussian_gradient(x, 0, 1)
            assert np.allclose(httpstan_grad, gradient)
