"""Test sampling from linear regression model."""
import numpy as np
import pytest

import helpers

headers = {"content-type": "application/json"}
program_code = """
    data {
        int<lower=0> N;
        int<lower=0> p;
        matrix[N,p] x;
        vector[N] y;
    }
    parameters {
        vector[p] beta;
        real<lower=0> sigma;
    }
    model {
        y ~ normal(x * beta, sigma);
    }
"""
np.random.seed(1)

n = 10000
p = 3

beta_true = beta_true = (1, 3, 5)
X = np.random.normal(size=(n, p))
X = (X - np.mean(X, axis=0)) / np.std(X, ddof=1, axis=0, keepdims=True)
y = np.dot(X, beta_true) + np.random.normal(size=n)
data = {"N": n, "p": p, "x": X.tolist(), "y": y.tolist()}


@pytest.mark.asyncio
async def test_linear_regression(api_url: str) -> None:
    """Test sampling from linear regression posterior with defaults."""

    payload = {
        "function": "stan::services::sample::hmc_nuts_diag_e_adapt",
        "data": data,
        "num_samples": 500,
        "num_warmup": 500,
    }
    beta_0 = await helpers.sample_then_extract(api_url, program_code, payload, "beta.1")
    assert all(np.abs(beta_0 - np.array(beta_true)[0]) < 0.05)
