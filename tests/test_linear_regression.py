"""Test sampling from linear regression model."""
import json

import aiohttp
import numpy as np


headers = {'content-type': 'application/json'}
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
data = {'N': n, 'p': p, 'x': X.tolist(), 'y': y.tolist()}


def test_linear_regression(loop_with_server, host, port):
    """Test sampling from linear regression posterior with defaults."""
    async def main():
        async with aiohttp.ClientSession() as session:
            programs_url = 'http://{}:{}/v1/programs'.format(host, port)
            payload = {'program_code': program_code}
            async with session.post(programs_url, data=json.dumps(payload), headers=headers) as resp:
                assert resp.status == 200
                program_id = (await resp.json())['id']

            programs_actions_url = 'http://{}:{}/v1/programs/{}/actions'.format(host, port, program_id)
            payload = {
                'type': 'stan::services::sample::hmc_nuts_diag_e_adapt',
                'data': data,
                'num_samples': 500,
                'num_warmup': 500,
            }

            # XXX: this function is repeated from programs_actions
            draws = []
            async with session.post(programs_actions_url, data=json.dumps(payload), headers=headers) as resp:
                assert resp.status == 200
                while True:
                    chunk = await resp.content.readline()
                    if not chunk:
                        break
                    assert len(chunk)
                    payload = json.loads(chunk)
                    assert len(payload) > 0
                    if payload['topic'] == 'SAMPLE':
                        assert isinstance(payload['feature'], dict)
                        if 'beta.1' in payload['feature']:
                            draws.append(payload['feature'])

            assert len(draws) > 0
            beta_0 = np.array([draw['beta.1']['doubleList']['value'].pop() for draw in draws])
            assert all(np.abs(beta_0 - np.array(beta_true)[0]) < 0.05)

    loop_with_server.run_until_complete(main())
