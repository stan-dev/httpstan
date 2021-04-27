"""Test deleting fits."""

import aiohttp
import pytest

import helpers

program_code = "parameters {real y;} model {y ~ normal(0,1);}"


@pytest.mark.asyncio
async def test_delete_fit(api_url: str) -> None:
    """Test deleting fit."""
    fit_payload = {"function": "stan::services::sample::hmc_nuts_diag_e_adapt"}
    operation = await helpers.sample(api_url, program_code, fit_payload)

    fit_name = operation["result"]["name"]

    async with aiohttp.ClientSession() as session:
        async with session.delete(f"{api_url}/{fit_name}") as resp:
            assert resp.status == 200

    # fit has been deleted, delete request should return 404
    async with aiohttp.ClientSession() as session:
        async with session.delete(f"{api_url}/{fit_name}") as resp:
            assert resp.status == 404
