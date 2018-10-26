"""Test Stan model compilation."""
import asyncio
import requests

import httpstan

program_code = "parameters {real y;} model {y ~ normal(0,1);}"


def test_models(httpstan_server):
    """Test compilation of an extension module."""

    host, port = httpstan_server.host, httpstan_server.port

    async def main():
        models_url = f"http://{host}:{port}/v1/models"
        resp = requests.post(models_url, json={"program_code": program_code})
        assert resp.status_code == 201
        assert "name" in resp.json()

    asyncio.get_event_loop().run_until_complete(main())


def test_calculate_model_name(httpstan_server):
    """Test model name calculation."""

    host, port = httpstan_server.host, httpstan_server.port

    async def main():
        models_url = f"http://{host}:{port}/v1/models"
        resp = requests.post(models_url, json={"program_code": program_code})
        assert resp.status_code == 201
        model_name = resp.json()["name"]
        assert len(model_name.split("/")[-1]) == 10
        assert model_name == httpstan.models.calculate_model_name(program_code)

    asyncio.get_event_loop().run_until_complete(main())
