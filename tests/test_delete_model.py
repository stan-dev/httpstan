"""Test delete model endpoint."""

import aiohttp
import pytest

program_code = "parameters {real z;} model {z ~ normal(0,1);}"


@pytest.mark.asyncio
async def test_delete_model(api_url: str) -> None:
    """Test that a model can be deleted."""

    payload = {"program_code": program_code}

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{api_url}/models", json=payload) as resp:
            assert resp.status == 201
            response_payload = await resp.json()
            assert "name" in response_payload

    model_name = response_payload["name"]

    async with aiohttp.ClientSession() as session:
        async with session.delete(f"{api_url}/{model_name}") as resp:
            assert resp.status == 200

    # model has been deleted, delete request should return 404
    async with aiohttp.ClientSession() as session:
        async with session.delete(f"{api_url}/{model_name}") as resp:
            assert resp.status == 404
