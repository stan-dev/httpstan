"""Test sampling."""
import aiohttp
import json
import statistics

import httpstan.callbacks_writer_pb2


host, port = '127.0.0.1', 8080
programs_url = 'http://{}:{}/v1/programs'.format(host, port)
program_code = 'parameters {real y;} model {y ~ normal(0,1);}'
headers = {'content-type': 'application/json'}


def test_programs_actions(loop_with_server):
    """Simple test of sampling."""
    async def main():
        async with aiohttp.ClientSession() as session:
            data = {'program_code': program_code}
            async with session.post(programs_url, data=json.dumps(data), headers=headers) as resp:
                assert resp.status == 200
                program_id = (await resp.json())['id']

            programs_actions_url = 'http://{}:{}/v1/programs/{}/actions'.format(host, port, program_id)
            num_samples = num_warmup = 500
            data = {
                'type': 'stan::services::sample::hmc_nuts_diag_e',
                'num_samples': num_samples,
                'num_warmup': num_warmup,
            }
            draws = []
            async with session.post(programs_actions_url, data=json.dumps(data), headers=headers) as resp:
                assert resp.status == 200
                while True:
                    chunk = await resp.content.readline()
                    if not chunk:
                        break
                    assert len(chunk)
                    payload = json.loads(chunk)
                    assert len(payload) > 0
                    assert 'topic' in payload
                    assert 'LOGGER' in httpstan.callbacks_writer_pb2.WriterMessage.Topic.keys()
                    assert 'SAMPLE' in httpstan.callbacks_writer_pb2.WriterMessage.Topic.keys()
                    if payload['topic'] == 'SAMPLE':
                        assert isinstance(payload['feature'], dict)
                        if 'y' in payload['feature']:
                            draws.append(payload['feature'])
            assert len(draws) > 0
            assert len(draws) == num_samples

            assert -5 < statistics.mean(draw['y']['doubleList']['value'].pop() for draw in draws) < 5

    loop_with_server.run_until_complete(main())


def test_programs_actions_bad_args(loop_with_server):
    """Test handler argument handling."""
    async def main(loop):
        async with aiohttp.ClientSession() as session:
            data = {'program_code': program_code}
            async with session.post(programs_url, data=json.dumps(data), headers=headers) as resp:
                assert resp.status == 200
                program_id = (await resp.json())['id']

            programs_actions_url = 'http://{}:{}/v1/programs/{}/actions'.format(host, port, program_id)
            data = {'wrong_key': 'wrong_value'}
            async with session.post(programs_actions_url, data=json.dumps(data), headers=headers) as resp:
                assert resp.status == 422
                assert await resp.json() == {'type': ['Missing data for required field.']}

    loop_with_server.run_until_complete(main(loop_with_server))
