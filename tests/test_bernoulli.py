"""Test sampling from Bernoulli model."""
import asyncio

import aiohttp
import pytest

import helpers

program_code = """
    data {
        int<lower=0> N;
        int<lower=0,upper=1> y[N];
    }
    parameters {
        real<lower=0,upper=1> theta;
    }
    model {
        theta ~ beta(1,1);
        for (n in 1:N)
        y[n] ~ bernoulli(theta);
    }
    """
data = {"N": 10, "y": (0, 1, 0, 0, 0, 0, 0, 0, 0, 1)}


@pytest.mark.asyncio
async def test_bernoulli(api_url: str) -> None:
    """Test sampling from Bernoulli model with defaults."""
    payload = {"function": "stan::services::sample::hmc_nuts_diag_e_adapt", "data": data}
    param_name = "theta"
    theta = await helpers.sample_then_extract(api_url, program_code, payload, param_name)
    assert len(theta) == 1_000


@pytest.mark.asyncio
async def test_bernoulli_params(api_url: str) -> None:
    """Test getting parameters from Bernoulli model."""

    model_name = await helpers.get_model_name(api_url, program_code)
    models_params_url = f"{api_url}/{model_name}/params"
    payload = {"data": data}
    async with aiohttp.ClientSession() as session:
        async with session.post(models_params_url, json=payload) as resp:
            assert resp.status == 200
            response_payload = await resp.json()
            assert "name" in response_payload and response_payload["name"] == model_name
            assert "params" in response_payload and len(response_payload["params"])
            params = response_payload["params"]
            param = params[0]
            assert param["name"] == "theta"
            assert param["dims"] == []
            assert param["constrained_names"] == ["theta"]


@pytest.mark.asyncio
async def test_bernoulli_params_out_of_bounds(api_url: str) -> None:
    """Test getting parameters from Bernoulli model error handling."""

    model_name = await helpers.get_model_name(api_url, program_code)
    models_params_url = f"{api_url}/{model_name}/params"
    # N = -5 in data is invalid according to program code
    payload = {"data": {"N": -5, "y": (0, 1, 0)}}
    async with aiohttp.ClientSession() as session:
        async with session.post(models_params_url, json=payload) as resp:
            assert resp.status == 400
            response_payload = await resp.json()
            assert "message" in response_payload
            assert "but must be greater than or equal to 0" in response_payload["message"]


@pytest.mark.asyncio
async def test_bernoulli_unacceptable_arg(api_url: str) -> None:
    """Test sampling from Bernoulli model with an unacceptable arg."""

    model_name = await helpers.get_model_name(api_url, program_code)
    fits_url = f"{api_url}/{model_name}/fits"
    payload = {"function": "invalid abcdef", "data": "string, not a dictionary"}
    async with aiohttp.ClientSession() as session:
        async with session.post(fits_url, json=payload) as resp:
            assert resp.status == 422
            assert "json" in (await resp.json()) and "data" in (await resp.json())["json"]


@pytest.mark.asyncio
async def test_bernoulli_unknown_arg(api_url: str) -> None:
    """Test sampling from Bernoulli model with an unknown arg."""

    model_name = await helpers.get_model_name(api_url, program_code)
    fits_url = f"{api_url}/{model_name}/fits"
    payload = {"function": "stan::services::sample::hmc_nuts_diag_e_adapt", "data": data, "unknown_arg": 9}
    async with aiohttp.ClientSession() as session:
        async with session.post(fits_url, json=payload) as resp:
            assert resp.status == 422
            assert "json" in (await resp.json()) and "unknown_arg" in (await resp.json())["json"]


@pytest.mark.asyncio
async def test_bernoulli_out_of_bounds(api_url: str) -> None:
    """Test sampling from Bernoulli model with out of bounds data.

    This error cannot be detected via schema validation.

    """

    # N = -5 in data is invalid according to program code
    payload = {
        "function": "stan::services::sample::hmc_nuts_diag_e_adapt",
        "data": {"N": -5, "y": (0, 1, 0, 0, 0, 0, 0, 0, 0, 1)},
    }
    operation = await helpers.sample(api_url, program_code, payload)
    error = operation["result"]
    assert "message" in error
    assert "but must be greater than or equal to 0" in error["message"]


@pytest.mark.asyncio
async def test_bernoulli_parallel(api_url: str) -> None:
    """Test sampling in parallel from Bernoulli model with defaults."""

    payload = {"function": "stan::services::sample::hmc_nuts_diag_e_adapt", "data": data}

    # launch `num_chains` sample operations in parallel
    num_chains = 3
    tasks_coros = [asyncio.ensure_future(helpers.sample(api_url, program_code, payload)) for _ in range(num_chains)]
    operations = [await coro for coro in tasks_coros]
    for operation in operations:
        fit_name = operation["result"]["name"]
        fit_url = f"{api_url}/{fit_name}"
        async with aiohttp.ClientSession() as session:
            async with session.get(fit_url) as resp:
                assert resp.status == 200
                assert resp.headers["Content-Type"] == "text/plain; charset=utf-8"
                theta = helpers.extract("theta", await resp.read())
                assert len(theta) == 1_000
