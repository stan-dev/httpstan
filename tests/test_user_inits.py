"""Test user-provided initial values for parameters."""
import asyncio
import typing
import random
import statistics

import requests

import helpers

program_code = """
    data {
      real x;
    }
    parameters {
      real mu;
    }
    model {
      x ~ normal(mu,1);
    }
"""
data = {"x": 2}


async def sample_then_extract_draws(
    api_url: str, program_code: str, sample_kwargs: dict, param_name: str
) -> typing.List[typing.Union[int, float]]:
    model_name = helpers.get_model_name(api_url, program_code)
    payload = sample_kwargs
    payload.update(**sample_kwargs)
    resp = requests.post(f"{api_url}/{model_name}/fits", json=payload)
    assert resp.status_code == 201
    operation = resp.json()
    operation_name = operation["name"]
    assert operation_name is not None
    assert operation_name.startswith("operations/")
    assert not operation["done"]

    fit_name = operation["metadata"]["fit"]["name"]

    resp = requests.get(f"{api_url}/{operation_name}")
    assert resp.status_code == 200, f"{api_url}/{operation_name}"
    assert not resp.json()["done"], resp.json()

    # wait until fit is finished
    while not requests.get(f"{api_url}/{operation_name}").json()["done"]:
        await asyncio.sleep(0.1)

    resp = requests.get(f"{api_url}/{fit_name}")
    assert resp.status_code == 200, resp.json()
    assert resp.headers["Content-Type"] == "application/octet-stream"
    fit_bytes = resp.content
    helpers.validate_protobuf_messages(fit_bytes)
    return helpers.extract_draws(fit_bytes, param_name)


def test_user_inits(api_url: str) -> None:
    """Test that user-provided initial values make some difference."""

    async def main() -> None:
        random_seed = random.randrange(2 ** 16) + 1

        sample_kwargs = {
            "function": "stan::services::sample::hmc_nuts_diag_e_adapt",
            "data": data,
            "num_samples": 10,
            "num_warmup": 0,
            "random_seed": random_seed,
        }
        param_name = "mu"
        draws1 = await sample_then_extract_draws(api_url, program_code, sample_kwargs, param_name)
        assert draws1 is not None

        sample_kwargs = {
            "function": "stan::services::sample::hmc_nuts_diag_e_adapt",
            "data": data,
            "num_samples": 10,
            "num_warmup": 0,
            "random_seed": random_seed,
            "init": {"mu": 400},
        }
        param_name = "mu"
        draws2 = await sample_then_extract_draws(api_url, program_code, sample_kwargs, param_name)
        assert draws2 is not None
        assert statistics.mean(draws1) != statistics.mean(draws2)

        sample_kwargs = {
            "function": "stan::services::sample::hmc_nuts_diag_e_adapt",
            "data": data,
            "num_samples": 10,
            "num_warmup": 0,
            "random_seed": random_seed,
            "init": {"mu": 4000},
        }
        param_name = "mu"
        draws3 = await sample_then_extract_draws(api_url, program_code, sample_kwargs, param_name)
        assert draws3 is not None
        assert statistics.mean(draws3) != statistics.mean(draws2)

    asyncio.get_event_loop().run_until_complete(main())


def test_user_inits_invalid_value(api_url: str) -> None:
    """Test providing an invalid `init` (e.g., a number)."""

    async def main() -> None:
        sample_kwargs = {
            "function": "stan::services::sample::hmc_nuts_diag_e_adapt",
            "data": data,
            "num_samples": 10,
            "num_warmup": 0,
            "init": -3,
        }
        model_name = helpers.get_model_name(api_url, program_code)
        payload = sample_kwargs
        payload.update(**sample_kwargs)
        resp = requests.post(f"{api_url}/{model_name}/fits", json=payload)
        assert resp.status_code == 422
        assert resp.json().get("init"), resp.json()
        assert resp.json()["init"]["_schema"].pop() == "Invalid input type."

    asyncio.get_event_loop().run_until_complete(main())
