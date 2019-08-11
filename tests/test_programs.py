"""Test Stan model compilation."""
import asyncio
import random
import requests
import string
from time import time

import httpstan

import helpers

program_code = "parameters {real y;} model {y ~ normal(0,1);}"


def test_models(api_url):
    """Test compilation of an extension module."""

    async def main():
        models_url = f"{api_url}/models"
        resp = requests.post(models_url, json={"program_code": program_code})
        assert resp.status_code == 201
        assert "name" in resp.json()

    asyncio.get_event_loop().run_until_complete(main())


def test_calculate_model_name(api_url):
    """Test model name calculation."""

    async def main():
        model_name = helpers.get_model_name(api_url, program_code)
        assert len(model_name.split("/")[-1]) == 10
        assert model_name == httpstan.models.calculate_model_name(program_code)

    asyncio.get_event_loop().run_until_complete(main())


def test_model_cache(api_url):
    """Test model cache."""
    # use random string, so the module name is new and compilation happens

    random_string = "".join(random.choices(string.ascii_letters, k=random.randint(10, 30)))

    program_code = "".join(
        ["parameters {real ", random_string, ";} model { ", random_string, " ~ std_normal();}"]
    )

    async def main():
        models_url = f"{api_url}/models"
        resp = requests.post(models_url, json={"program_code": program_code})
        assert resp.status_code == 201
        assert "name" in resp.json()

    ts1 = time()
    asyncio.get_event_loop().run_until_complete(main())
    duration_compilation = time() - ts1

    ts2 = time()
    asyncio.get_event_loop().run_until_complete(main())
    duration_cache = time() - ts2

    # force duration_cache > 0
    duration_cache += 1e-9
    assert (duration_compilation / duration_cache) > 10
