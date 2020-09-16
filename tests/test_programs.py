"""Test Stan model compilation."""
import random
import string
from time import time

import aiohttp
import pytest

import httpstan.models

import helpers

program_code = "parameters {real y;} model {y ~ normal(0,1);}"


@pytest.mark.asyncio
async def test_create_model(api_url: str) -> None:
    """Test compilation of an extension module."""

    models_url = f"{api_url}/models"
    payload = {"program_code": program_code}
    async with aiohttp.ClientSession() as session:
        async with session.post(models_url, json=payload) as resp:
            assert resp.status == 201
            response_payload = await resp.json()
            assert "name" in response_payload


@pytest.mark.asyncio
async def test_list_models(api_url: str) -> None:
    """Test cached model listing."""

    models_url = f"{api_url}/models"
    payload = {"program_code": program_code}
    async with aiohttp.ClientSession() as session:
        async with session.get(models_url, json=payload) as resp:
            assert resp.status == 200
            response_payload = await resp.json()
    assert "models" in response_payload
    assert "name" in response_payload["models"].pop()
    assert "compiler_output" in response_payload["models"].pop()
    assert "stanc_warnings" in response_payload["models"].pop()


@pytest.mark.asyncio
async def test_calculate_model_name(api_url: str) -> None:
    """Test model name calculation."""
    model_name = await helpers.get_model_name(api_url, program_code)
    assert model_name == httpstan.models.calculate_model_name(program_code)


@pytest.mark.asyncio
async def test_model_cache(api_url: str) -> None:
    """Test model cache."""
    # use random string, so the module name is new and compilation happens

    random_string = "".join(random.choices(string.ascii_letters, k=random.randint(10, 30)))

    program_code = "".join(["parameters {real ", random_string, ";} model { ", random_string, " ~ std_normal();}"])

    ts1 = time()
    await helpers.get_model_name(api_url, program_code)
    duration_compilation = time() - ts1

    ts2 = time()
    await helpers.get_model_name(api_url, program_code)
    duration_cache = time() - ts2

    # force duration_cache > 0
    duration_cache += 1e-9
    assert (duration_compilation / duration_cache) > 10
