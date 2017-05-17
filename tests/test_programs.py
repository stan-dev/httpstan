"""Test Stan Program compilation."""
import aiohttp
import json


host, port = '127.0.0.1', 8080
url = 'http://{}:{}/v1/programs'.format(host, port)
program_code = 'parameters {real y;} model {y ~ normal(0,1);}'
headers = {'content-type': 'application/json'}


def test_programs(loop_with_server):
    """Test compilation of an extension module."""
    async def main(loop):
        async with aiohttp.ClientSession() as session:
            data = {'program_code': program_code}
            async with session.post(url, data=json.dumps(data), headers=headers) as resp:
                assert resp.status == 200
                payload = await resp.json()
                assert 'program' in payload and 'id' in payload['program']

    loop_with_server.run_until_complete(main(loop_with_server))
