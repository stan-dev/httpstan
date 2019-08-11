"""Test sampling from linear regression model."""
import asyncio

import numpy as np
import requests

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


def test_linear_regression(api_url: str) -> None:
    """Test sampling from linear regression posterior with defaults."""

    async def main() -> None:
        model_name = helpers.get_model_name(api_url, program_code)
        fits_url = f"{api_url}/models/{model_name.split('/')[-1]}/fits"
        payload = {
            "function": "stan::services::sample::hmc_nuts_diag_e_adapt",
            "data": data,
            "num_samples": 500,
            "num_warmup": 500,
        }
        resp = requests.post(fits_url, json=payload)
        assert resp.status_code == 201
        operation = resp.json()
        operation_name = operation["name"]
        assert operation_name is not None
        assert operation_name.startswith("operations/")
        assert not operation["done"]

        fit_name = operation["metadata"]["fit"]["name"]

        resp = requests.get(f"{api_url}/{operation_name}")
        assert resp.status_code == 200, f"{api_url}/{operation_name}"
        assert not resp.json()["done"], resp.json()

        # wait until fit is finished
        while not requests.get(f"{api_url}/{operation_name}").json()["done"]:
            await asyncio.sleep(0.1)

        assert fit_name.startswith("models/") and "fits" in fit_name
        fit_url = f"{api_url}/{fit_name}"
        resp = requests.get(fit_url)
        assert resp.status_code == 200
        fit_bytes = resp.content
        beta_0 = helpers.extract_draws(fit_bytes, "beta.1")
        assert all(np.abs(beta_0 - np.array(beta_true)[0]) < 0.05)

    asyncio.get_event_loop().run_until_complete(main())
