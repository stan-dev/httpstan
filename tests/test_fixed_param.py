"""Test sampling from Bernoulli model with fixed_param "method"."""
import numpy as np
import pytest

import helpers

program_code = """
    data {
        int<lower=0> N;
        array[N] int<lower=0,upper=1> y;
    }
    parameters {
        real<lower=0,upper=1> theta;
    }
    model {
        theta ~ beta(1,1);
        for (n in 1:N)
        y[n] ~ bernoulli(theta);
    }
    """
data = {"N": 10, "y": (0, 1, 0, 0, 0, 0, 0, 0, 0, 1)}


@pytest.mark.asyncio
async def test_bernoulli_fixed_param(api_url: str) -> None:
    """Test sampling from Bernoulli model with defaults and fixed_param method."""
    payload = {"function": "stan::services::sample::fixed_param", "data": data}
    param_name = "theta"
    theta = await helpers.sample_then_extract(api_url, program_code, payload, param_name)
    assert len(theta) == 1_000
    np.testing.assert_allclose(theta, theta[0])
