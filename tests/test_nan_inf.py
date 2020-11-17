"""Test serialization of nan and inf values."""
import math

import pytest

import helpers

program_code = """
    parameters {
      real eta;
    }
    transformed parameters {
      real alpha;
      real beta;
      real gamma;
      alpha = not_a_number();
      beta = positive_infinity();
      gamma = negative_infinity();
    }
    model {
      target += normal_lpdf(eta | 0, 1);
    }
"""


@pytest.mark.asyncio
async def test_nan_inf(api_url: str) -> None:
    payload = {"function": "stan::services::sample::hmc_nuts_diag_e_adapt", "num_samples": 10, "num_warmup": 10}
    alpha = await helpers.sample_then_extract(api_url, program_code, payload, "alpha")
    assert len(alpha) == 10
    assert math.isnan(alpha[0])
    beta = await helpers.sample_then_extract(api_url, program_code, payload, "beta")
    assert math.isinf(beta[0])
    gamma = await helpers.sample_then_extract(api_url, program_code, payload, "gamma")
    assert math.isinf(gamma[0])
