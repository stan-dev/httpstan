"""Test Stan model compilation."""
import aiohttp
import json


headers = {'content-type': 'application/json'}
program_code = 'parameters {real y;} model {y ~ normal(0,1);}'


def test_models(loop_with_server, host, port):
    """Test compilation of an extension module."""
    async def main():
        async with aiohttp.ClientSession() as session:
            data = {'program_code': program_code}
            models_url = 'http://{}:{}/v1/models'.format(host, port)
            async with session.post(models_url, data=json.dumps(data), headers=headers) as resp:
                assert resp.status == 200
                payload = await resp.json()
                assert 'id' in payload

    loop_with_server.run_until_complete(main())
