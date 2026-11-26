"""Windows-only regression: independent model DLLs, spawn and cache deletion."""

import asyncio
import sys

import aiohttp
import pytest

import httpstan.cache
import httpstan.models

import helpers

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific native runtime"),
    pytest.mark.asyncio,
]


async def test_windows_models(api_url: str) -> None:
    code = "parameters {real windows_y;} model {windows_y ~ normal(0,1);}"
    code2 = "parameters {real windows_z;} model {windows_z ~ normal(2,1);}"
    name = await helpers.get_model_name(api_url, code)
    name2 = await helpers.get_model_name(api_url, code2)
    first = httpstan.models.import_services_extension_module(name)
    second = httpstan.models.import_services_extension_module(name2)
    assert first.__file__ != second.__file__
    assert first is httpstan.models.import_services_extension_module(name)
    print("[smoke] model modules:", first.__file__, second.__file__, flush=True)

    async def sample(chain: int) -> None:
        operation = await helpers.sample(
            api_url,
            code,
            {
                "function": "stan::services::sample::hmc_nuts_diag_e_adapt",
                "data": {},
                "num_warmup": 20,
                "num_samples": 12,
                "chain": chain,
                "random_seed": 111 + chain,
            },
        )
        print(f"[smoke] chain {chain}: {operation}", flush=True)
        fit = await helpers.fit_bytes(api_url, operation["result"]["name"])
        assert len(helpers.extract("windows_y", fit)) == 12

    await asyncio.wait_for(asyncio.gather(sample(1), sample(2)), timeout=180)
    async with aiohttp.ClientSession() as session:
        async with session.delete(f"{api_url}/{name}") as resp:
            assert resp.status == 200, await resp.text()
        assert not httpstan.cache.model_directory(name).exists()
        assert name not in httpstan.cache.list_model_names()
        async with session.delete(f"{api_url}/{name}") as resp:
            assert resp.status == 404, await resp.text()
    assert await helpers.get_model_name(api_url, code) == name
    rebuilt = httpstan.models.import_services_extension_module(name)
    assert rebuilt.__file__ != first.__file__
    await asyncio.wait_for(sample(3), timeout=180)
