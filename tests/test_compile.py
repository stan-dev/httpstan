"""Test compiling functions."""

import aiohttp
import pytest


@pytest.mark.asyncio
async def test_compile_invalid_distribution(api_url: str) -> None:
    """Check that compiler error is returned to client."""

    program_code = "parameters {real z;} model {z ~ no_such_distribution();}"
    payload = {"program_code": program_code}
    models_url = f"{api_url}/models"
    async with aiohttp.ClientSession() as session:
        async with session.post(models_url, json=payload) as resp:
            assert resp.status == 400
            response_payload = await resp.json()
    assert "message" in response_payload
    assert "Probability function must end in _lpdf" in response_payload["message"]


@pytest.mark.asyncio
async def test_compile_unknown_arg(api_url: str) -> None:
    """Check that compiler error is returned to client.

    This error can be detected by schema validation.

    """

    program_code = "parameters {real z;} model {z ~ no_such_distribution();}"
    payload = {"unknown_arg": "abcdef", "program_code": program_code}
    models_url = f"{api_url}/models"
    async with aiohttp.ClientSession() as session:
        async with session.post(models_url, json=payload) as resp:
            assert resp.status == 422
            response_payload = await resp.json()
    assert "unknown_arg" in response_payload
