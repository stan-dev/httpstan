"""Test Stan model compilation."""
import asyncio
import json

import aiohttp

import httpstan

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
                assert resp.status == 201
                payload = await resp.json()
                assert "name" in payload

    asyncio.get_event_loop().run_until_complete(main())


def test_calculate_model_name(httpstan_server):
    """Test model name calculation."""

    host, port = httpstan_server.host, httpstan_server.port

    async def main():
        async with aiohttp.ClientSession() as session:
            data = {"program_code": program_code}
            models_url = "http://{}:{}/v1/models".format(host, port)
            async with session.post(models_url, data=json.dumps(data), headers=headers) as resp:
                assert resp.status == 201
                payload = await resp.json()
                model_name = payload["name"]
            assert len(model_name.split("/")[-1]) == 10
            assert model_name == httpstan.models.calculate_model_name(program_code)

    asyncio.get_event_loop().run_until_complete(main())
