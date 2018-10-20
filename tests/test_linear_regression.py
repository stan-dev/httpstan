"""Test sampling from linear regression model."""
import asyncio
import json

import aiohttp
import numpy as np

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


def test_linear_regression(httpstan_server):
    """Test sampling from linear regression posterior with defaults."""

    host, port = httpstan_server.host, httpstan_server.port

    async def main():
        async with aiohttp.ClientSession() as session:
            models_url = "http://{}:{}/v1/models".format(host, port)
            payload = {"program_code": program_code}
            async with session.post(models_url, data=json.dumps(payload), headers=headers) as resp:
                assert resp.status == 201
                model_id = (await resp.json())["id"]

            models_actions_url = "http://{}:{}/v1/models/{}/actions".format(host, port, model_id)
            payload = {
                "type": "stan::services::sample::hmc_nuts_diag_e_adapt",
                "data": data,
                "num_samples": 500,
                "num_warmup": 500,
            }

            async with session.post(
                models_actions_url, data=json.dumps(payload), headers=headers
            ) as resp:
                beta_0 = await helpers.extract_draws(resp, "beta.1")
            assert all(np.abs(beta_0 - np.array(beta_true)[0]) < 0.05)

    asyncio.get_event_loop().run_until_complete(main())
