"""Test sampling from Bernoulli model."""
import asyncio
import json

import google.protobuf.internal.decoder
import httpstan.callbacks_writer_pb2 as callbacks_writer_pb2
import aiohttp

import helpers


headers = {"content-type": "application/json"}
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


def test_bernoulli(httpstan_server):
    """Test sampling from Bernoulli model with defaults."""
    host, port = httpstan_server.host, httpstan_server.port

    async def main():
        models_url = "http://{}:{}/v1/models".format(host, port)
        payload = {"program_code": program_code}
        async with aiohttp.ClientSession() as session:
            async with session.post(models_url, data=json.dumps(payload), headers=headers) as resp:
                assert resp.status == 201
                model_name = (await resp.json())["name"]

        fits_url = f"http://{host}:{port}/v1/models/{model_name.split('/')[-1]}/fits"
        payload = {"function": "stan::services::sample::hmc_nuts_diag_e_adapt", "data": data}
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
                assert resp.status == 200
                assert resp.content_type == "application/octet-stream"
                fit_bytes = await resp.read()
                helpers.validate_protobuf_messages(fit_bytes)

    asyncio.get_event_loop().run_until_complete(main())


def test_bernoulli_params(httpstan_server):
    """Test getting parameters from Bernoulli model."""

    host, port = httpstan_server.host, httpstan_server.port

    async def main():
        async with aiohttp.ClientSession() as session:
            models_url = "http://{}:{}/v1/models".format(host, port)
            payload = {"program_code": program_code}
            async with session.post(models_url, data=json.dumps(payload), headers=headers) as resp:
                assert resp.status == 201
                model_name = (await resp.json())["name"]

            models_params_url = f"http://{host}:{port}/v1/models/{model_name.split('/')[-1]}/params"
            payload = {"data": data}
            async with session.post(
                models_params_url, data=json.dumps(payload), headers=headers
            ) as resp:
                assert resp.status == 200
                response_payload = await resp.json()
                assert "name" in response_payload and response_payload["name"] == model_name
                assert "params" in response_payload and len(response_payload["params"])
                params = response_payload["params"]
                param = params[0]
                assert param["name"] == "theta"
                assert param["dims"] == []
                assert param["constrained_names"] == ["theta"]

    asyncio.get_event_loop().run_until_complete(main())
