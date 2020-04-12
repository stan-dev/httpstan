"""Test sampling from Bernoulli model."""
import aiohttp
import pytest

import helpers

program_code = "parameters {real y;} model {y ~ normal(0,1);}"


@pytest.mark.asyncio
async def test_logger_callback(api_url: str) -> None:
    """Test that operation progress has been updated."""

    payload = {"function": "stan::services::sample::hmc_nuts_diag_e_adapt"}
    operation = await helpers.sample(api_url, program_code, payload)
    operation_name = operation["name"]
    operation_url = f"{api_url}/{operation_name}"
    async with aiohttp.ClientSession() as session:
        async with session.get(operation_url) as resp:
            assert resp.status == 200
            operation = await resp.json()
            assert operation["name"] == operation_name
            progress = operation["metadata"]["progress"]
            assert progress == "Iteration: 2000 / 2000 [100%]  (Sampling)"
