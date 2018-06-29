"""Test Stan model compilation."""
import asyncio
import aiohttp
import json


headers = {"content-type": "application/json"}
program_code = "parameters {real y;} model {y ~ normal(0,1);}"


def test_models(httpstan_server):
    """Test compilation of an extension module."""

    host, port = httpstan_server.host, httpstan_server.port

    async def main():
        async with aiohttp.ClientSession() as session:
            data = {"program_code": program_code}
            models_url = "http://{}:{}/v1/models".format(host, port)
            async with session.post(models_url, data=json.dumps(data), headers=headers) as resp:
                assert resp.status == 200
                payload = await resp.json()
                assert "id" in payload

    asyncio.get_event_loop().run_until_complete(main())
