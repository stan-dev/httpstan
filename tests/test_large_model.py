"""Test sampling from a model with many parameters."""
import pytest

import helpers

program_code = """
    data {
      int<lower=0> J; // number of schools
      array[J] real y; // estimated treatment effects
      array[J] real<lower=0> sigma; // s.e. of effect estimates
    }
    parameters {
      real mu;
      real<lower=0> tau;
      array[J] real eta;
    }
    transformed parameters {
      array[J] real theta;
      for (j in 1:J)
        theta[j] = mu + tau * eta[j];
    }
    model {
      target += normal_lpdf(eta | 0, 1);
      target += normal_lpdf(y | theta, sigma);
    }
"""
schools_data = {"J": 8 * 20, "y": (28, 8, -3, 7, -1, 1, 18, 12) * 20, "sigma": (15, 10, 16, 11, 9, 11, 10, 18) * 20}


@pytest.mark.asyncio
async def test_eight_schools_large(api_url: str) -> None:
    payload = {
        "function": "stan::services::sample::hmc_nuts_diag_e_adapt",
        "data": schools_data,
        "num_samples": 100,
        "num_warmup": 100,
    }
    param_name = "mu"
    mu = await helpers.sample_then_extract(api_url, program_code, payload, param_name)
    assert len(mu) == 100
