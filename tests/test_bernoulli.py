"""Test sampling from Bernoulli model."""
import asyncio

import requests

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


def test_bernoulli(api_url):
    """Test sampling from Bernoulli model with defaults."""

    async def main():
        model_name = helpers.get_model_name(api_url, program_code)
        payload = {"function": "stan::services::sample::hmc_nuts_diag_e_adapt", "data": data}
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

    asyncio.get_event_loop().run_until_complete(main())


def test_bernoulli_params(api_url):
    """Test getting parameters from Bernoulli model."""

    async def main():
        model_name = helpers.get_model_name(api_url, program_code)
        models_params_url = f"{api_url}/models/{model_name.split('/')[-1]}/params"
        resp = requests.post(models_params_url, json={"data": data})
        assert resp.status_code == 200
        response_payload = resp.json()
        assert "name" in response_payload and response_payload["name"] == model_name
        assert "params" in response_payload and len(response_payload["params"])
        params = response_payload["params"]
        param = params[0]
        assert param["name"] == "theta"
        assert param["dims"] == []
        assert param["constrained_names"] == ["theta"]

    asyncio.get_event_loop().run_until_complete(main())


def test_bernoulli_params_out_of_bounds(api_url):
    """Test getting parameters from Bernoulli model error handling."""

    async def main():
        model_name = helpers.get_model_name(api_url, program_code)
        models_params_url = f"{api_url}/models/{model_name.split('/')[-1]}/params"
        # N = -5 in data is invalid according to program code
        resp = requests.post(models_params_url, json={"data": {"N": -5, "y": (0, 1, 0)}})
        assert resp.status_code == 400
        resp_dict = resp.json()
        assert "message" in resp_dict
        assert "Found negative dimension size" in resp_dict["message"]

    asyncio.get_event_loop().run_until_complete(main())


def test_bernoulli_invalid_arg(api_url):
    """Test sampling from Bernoulli model with invalid arg."""

    async def main():
        model_name = helpers.get_model_name(api_url, program_code)
        fits_url = f"{api_url}/models/{model_name.split('/')[-1]}/fits"
        payload = {
            "function": "stan::services::sample::hmc_nuts_diag_e_adapt",
            "data": data,
            "invalid_arg": 9,
        }
        resp = requests.post(fits_url, json=payload)
        assert resp.status_code == 201
        operation_name = resp.json()["name"]
        # wait until fit is finished
        while not requests.get(f"{api_url}/{operation_name}").json()["done"]:
            await asyncio.sleep(0.1)
        operation = requests.get(f"{api_url}/{operation_name}").json()
        error = operation["result"]
        assert "message" in error
        assert "got an unexpected keyword argument" in error["message"]

    asyncio.get_event_loop().run_until_complete(main())


def test_bernoulli_out_of_bounds(api_url):
    """Test sampling from Bernoulli model with out of bounds data."""

    async def main():
        model_name = helpers.get_model_name(api_url, program_code)
        fits_url = f"{api_url}/models/{model_name.split('/')[-1]}/fits"
        # N = -5 in data is invalid according to program code
        payload = {
            "function": "stan::services::sample::hmc_nuts_diag_e_adapt",
            "data": {"N": -5, "y": (0, 1, 0, 0, 0, 0, 0, 0, 0, 1)},
        }
        resp = requests.post(fits_url, json=payload)
        assert resp.status_code == 201
        operation_name = resp.json()["name"]
        # wait until fit is finished
        while not requests.get(f"{api_url}/{operation_name}").json()["done"]:
            await asyncio.sleep(0.1)
        operation = requests.get(f"{api_url}/{operation_name}").json()
        error = operation["result"]
        assert "message" in error
        assert "Found negative dimension size" in error["message"]

    asyncio.get_event_loop().run_until_complete(main())
