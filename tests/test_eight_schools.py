"""Test sampling from Eight Schools model."""
import asyncio
import json

import aiohttp

import helpers


headers = {"content-type": "application/json"}
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


def test_eight_schools(httpstan_server):
    """Test sampling from Eight Schools model with defaults."""

    host, port = httpstan_server.host, httpstan_server.port

    async def main():
        async with aiohttp.ClientSession() as session:
            models_url = "http://{}:{}/v1/models".format(host, port)
            payload = {"program_code": program_code}
            async with session.post(models_url, data=json.dumps(payload), headers=headers) as resp:
                assert resp.status == 201
                model_name = (await resp.json())["name"]

        fits_url = f"http://{host}:{port}/v1/models/{model_name.split('/')[-1]}/fits"
        payload = {
            "function": "stan::services::sample::hmc_nuts_diag_e_adapt",
            "data": schools_data,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(fits_url, data=json.dumps(payload), headers=headers) as resp:
                assert resp.status == 201, await resp.text()
                fit_name = (await resp.json())["name"]
                assert fit_name is not None
                assert fit_name.startswith("models/") and "fits" in fit_name
                assert resp.content_type == "application/json"

        async with aiohttp.ClientSession() as session:
            fit_url = f"http://{host}:{port}/v1/{fit_name}"
            async with session.get(fit_url, headers=headers) as resp:
                assert resp.status == 200, await resp.text()
                assert resp.content_type == "application/octet-stream"
                fit_bytes = await resp.read()
                helpers.validate_protobuf_messages(fit_bytes)

    asyncio.get_event_loop().run_until_complete(main())


def test_eight_schools_params(httpstan_server):
    """Test getting parameters from Eight Schools model."""

    host, port = httpstan_server.host, httpstan_server.port

    async def main():
        async with aiohttp.ClientSession() as session:
            models_url = "http://{}:{}/v1/models".format(host, port)
            payload = {"program_code": program_code}
            async with session.post(models_url, data=json.dumps(payload), headers=headers) as resp:
                assert resp.status == 201
                model_name = (await resp.json())["name"]

            models_params_url = f"http://{host}:{port}/v1/models/{model_name.split('/')[-1]}/params"
            payload = {"data": schools_data}
            async with session.post(
                models_params_url, data=json.dumps(payload), headers=headers
            ) as resp:
                assert resp.status == 200
                response_payload = await resp.json()
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
                assert param["constrained_names"] == [
                    f"eta.{i}" for i in range(1, schools_data["J"] + 1)
                ]

    asyncio.get_event_loop().run_until_complete(main())
