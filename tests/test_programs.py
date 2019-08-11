"""Test Stan model compilation."""
import asyncio
import requests

import httpstan

import helpers

program_code = "parameters {real y;} model {y ~ normal(0,1);}"


def test_models(api_url: str) -> None:
    """Test compilation of an extension module."""

    async def main() -> None:
        models_url = f"{api_url}/models"
        resp = requests.post(models_url, json={"program_code": program_code})
        assert resp.status_code == 201
        assert "name" in resp.json()

    asyncio.get_event_loop().run_until_complete(main())


def test_calculate_model_name(api_url: str) -> None:
    """Test model name calculation."""

    async def main() -> None:
        model_name = helpers.get_model_name(api_url, program_code)
        assert len(model_name.split("/")[-1]) == 10
        assert model_name == httpstan.models.calculate_model_name(program_code)

    asyncio.get_event_loop().run_until_complete(main())
