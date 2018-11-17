"""Test sampling from Eight Schools model."""
import asyncio

import requests

import helpers


program_code = """
    data {
      int<lower=0> J; // number of schools
      real y[J]; // estimated treatment effects
      real<lower=0> sigma[J]; // s.e. of effect estimates
    }
    parameters {
      real mu;
      real<lower=0> tau;
      real eta[J];
    }
    transformed parameters {
      real theta[J];
      for (j in 1:J)
        theta[j] = mu + tau * eta[j];
    }
    model {
      target += normal_lpdf(eta | 0, 1);
      target += normal_lpdf(y | theta, sigma);
    }
"""
schools_data = {
    "J": 8,
    "y": (28, 8, -3, 7, -1, 1, 18, 12),
    "sigma": (15, 10, 16, 11, 9, 11, 10, 18),
}


def test_eight_schools(api_url):
    """Test sampling from Eight Schools model with defaults."""

    async def main():
        model_name = helpers.get_model_name(api_url, program_code)
        fits_url = f"{api_url}/models/{model_name.split('/')[-1]}/fits"
        payload = {
            "function": "stan::services::sample::hmc_nuts_diag_e_adapt",
            "data": schools_data,
        }
        resp = requests.post(fits_url, json=payload)
        assert resp.status_code == 201, resp.content
        assert resp.headers["Content-Type"].split(";")[0] == "application/json"

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

        fit_url = f"{api_url}/{fit_name}"
        resp = requests.get(fit_url, json=payload)
        assert resp.status_code == 200
        assert resp.headers["Content-Type"] == "application/octet-stream"
        fit_bytes = resp.content
        helpers.validate_protobuf_messages(fit_bytes)

    asyncio.get_event_loop().run_until_complete(main())


def test_eight_schools_params(api_url):
    """Test getting parameters from Eight Schools model."""

    async def main():
        model_name = helpers.get_model_name(api_url, program_code)
        models_params_url = f"{api_url}/models/{model_name.split('/')[-1]}/params"
        resp = requests.post(models_params_url, json={"data": schools_data})
        assert resp.status_code == 200
        response_payload = resp.json()
        assert "name" in response_payload and response_payload["name"] == model_name
        assert "params" in response_payload and len(response_payload["params"])
        params = response_payload["params"]
        param = params[0]
        assert param["name"] == "mu"
        assert param["dims"] == []
        assert param["constrained_names"] == ["mu"]
        param = params[1]
        assert param["name"] == "tau"
        assert param["dims"] == []
        assert param["constrained_names"] == ["tau"]
        param = params[2]
        assert param["name"] == "eta"
        assert param["dims"] == [schools_data["J"]]
        assert param["constrained_names"] == [f"eta.{i}" for i in range(1, schools_data["J"] + 1)]

    asyncio.get_event_loop().run_until_complete(main())
