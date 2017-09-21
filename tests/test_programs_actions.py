"""Test sampling."""
import aiohttp
import json
import statistics

import helpers

headers = {'content-type': 'application/json'}
program_code = 'parameters {real y;} model {y ~ normal(0,1);}'


def test_models_actions(loop_with_server, host, port):
    """Simple test of sampling."""
    async def main():
        async with aiohttp.ClientSession() as session:
            models_url = 'http://{}:{}/v1/models'.format(host, port)
            data = {'program_code': program_code}
            async with session.post(models_url, data=json.dumps(data), headers=headers) as resp:
                assert resp.status == 200
                model_id = (await resp.json())['id']

            models_actions_url = 'http://{}:{}/v1/models/{}/actions'.format(host, port, model_id)
            num_samples = num_warmup = 500
            data = {
                'type': 'stan::services::sample::hmc_nuts_diag_e',
                'num_samples': num_samples,
                'num_warmup': num_warmup,
            }
            async with session.post(models_actions_url, data=json.dumps(data), headers=headers) as resp:
                draws = await helpers.extract_draws(resp, 'y')
            assert -5 < statistics.mean(draws) < 5

    loop_with_server.run_until_complete(main())


def test_models_actions_bad_args(loop_with_server, host, port):
    """Test handler argument handling."""
    async def main(loop):
        async with aiohttp.ClientSession() as session:
            data = {'program_code': program_code}
            models_url = 'http://{}:{}/v1/models'.format(host, port)
            async with session.post(models_url, data=json.dumps(data), headers=headers) as resp:
                assert resp.status == 200
                model_id = (await resp.json())['id']

            models_actions_url = 'http://{}:{}/v1/models/{}/actions'.format(host, port, model_id)
            data = {'wrong_key': 'wrong_value'}
            async with session.post(models_actions_url, data=json.dumps(data), headers=headers) as resp:
                assert resp.status == 422
                assert await resp.json() == {'type': ['Missing data for required field.']}

    loop_with_server.run_until_complete(main(loop_with_server))
