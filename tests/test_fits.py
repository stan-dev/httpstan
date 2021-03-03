"""Test sampling."""
import statistics
from typing import Any, Dict, List, Optional, Union

import aiohttp
import numpy as np
import pytest

import helpers

headers = {"content-type": "application/json"}
program_code = "parameters {real y;} model {y ~ normal(0, 0.0001);}"
program_code_vector = "parameters {vector[2] z; vector[0] x;} model {z ~ normal(0, 0.0001);}"


@pytest.mark.asyncio
async def test_fits(api_url: str) -> None:
    """Simple test of sampling."""

    num_samples = num_warmup = 5000
    payload = {
        "function": "stan::services::sample::hmc_nuts_diag_e_adapt",
        "num_samples": num_samples,
        "num_warmup": num_warmup,
    }
    param_name = "y"
    draws = await helpers.sample_then_extract(api_url, program_code, payload, param_name)
    assert len(draws) == num_samples, (len(draws), num_samples)
    assert -0.01 < statistics.mean(draws) < 0.01


@pytest.mark.asyncio
async def test_models_actions_bad_args(api_url: str) -> None:
    """Test handler argument handling."""

    model_name = await helpers.get_model_name(api_url, program_code)
    fits_url = f"{api_url}/models/{model_name.split('/')[-1]}/fits"
    payload = {"wrong_key": "wrong_value"}
    async with aiohttp.ClientSession() as session:
        async with session.post(fits_url, json=payload) as resp:
            assert resp.status == 422
            response_dict = await resp.json()
            assert "json" in response_dict
            assert response_dict["json"] == {
                "function": ["Missing data for required field."],
                "wrong_key": ["Unknown field."],
            }


@pytest.mark.asyncio
async def test_fits_random_seed(api_url: str) -> None:
    """Simple test of sampling with fixed random seed."""

    async def draws(random_seed: Optional[int] = None) -> List[Union[int, float]]:
        payload: Dict[str, Any] = {"function": "stan::services::sample::hmc_nuts_diag_e_adapt"}
        if random_seed is not None:
            payload["random_seed"] = random_seed
        param_name = "y"
        return await helpers.sample_then_extract(api_url, program_code, payload, param_name)

    draws1 = np.array(await draws(random_seed=123))
    draws2 = np.array(await draws(random_seed=123))
    draws3 = np.array(await draws(random_seed=456))
    draws4 = np.array(await draws())

    assert draws1[0] == draws2[0] != draws4[0]
    assert draws2[0] != draws4[0]
    assert draws1[0] != draws3[0] != draws4[0]
    # look at all draws
    assert np.allclose(draws1, draws2)
    assert not np.allclose(draws1, draws3)


@pytest.mark.asyncio
async def test_fits_vector_sizes(api_url: str) -> None:
    """Simple test of sampling with zero and non-zero vector sizes."""

    num_samples = num_warmup = 500
    payload = {
        "function": "stan::services::sample::hmc_nuts_diag_e_adapt",
        "random_seed": 123,
        "num_samples": num_samples,
        "num_warmup": num_warmup,
    }
    param_name = "z.1"
    draws = await helpers.sample_then_extract(api_url, program_code_vector, payload, param_name)
    assert len(draws) == num_samples, (len(draws), num_samples)

    param_name = "z.2"
    draws = await helpers.sample_then_extract(api_url, program_code_vector, payload, param_name)
    assert len(draws) == num_samples, (len(draws), num_samples)

    param_name = "x.1"
    with pytest.raises(KeyError, match="No draws found for parameter `x.1`."):
        await helpers.sample_then_extract(api_url, program_code_vector, payload, param_name)
