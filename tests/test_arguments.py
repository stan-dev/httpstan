"""Test services function argument lookups."""
import asyncio

import requests

import httpstan.models
import httpstan.services.arguments as arguments

program_code = "parameters {real y;} model {y ~ normal(0,1);}"


def test_lookup_default():
    """Test argument default value lookup."""
    expected = 1000
    assert expected == arguments.lookup_default(arguments.Method.SAMPLE, "num_samples")
    expected = 0.05
    assert expected == arguments.lookup_default(arguments.Method.SAMPLE, "gamma")


def test_function_arguments(httpstan_server):
    """Test function argument name lookup."""
    host, port = httpstan_server.host, httpstan_server.port

    # function_arguments needs compiled module, so we have to get one
    async def main():
        models_url = f"http://{host}:{port}/v1/models"
        resp = requests.post(models_url, json={"program_code": program_code})
        assert resp.status_code == 201
        model_name = resp.json()["name"]

        # get a reference to the model_module
        app = {}  # mock aiohttp.web.Application
        await httpstan.cache.init_cache(app)  # setup database, populates app['db']
        module_bytes = await httpstan.cache.load_model_extension_module(model_name, app["db"])
        assert module_bytes is not None
        model_module = httpstan.models.import_model_extension_module(model_name, module_bytes)

        expected = [
            "random_seed",
            "chain",
            "init_radius",
            "num_warmup",
            "num_samples",
            "num_thin",
            "save_warmup",
            "refresh",
            "stepsize",
            "stepsize_jitter",
            "max_depth",
        ]

        assert expected == arguments.function_arguments("hmc_nuts_diag_e", model_module)

    asyncio.get_event_loop().run_until_complete(main())
