"""Test services function argument lookups."""
import asyncio
import json

import aiohttp

import httpstan.models
import httpstan.services.arguments as arguments

program_code = "parameters {real y;} model {y ~ normal(0,1);}"
headers = {"content-type": "application/json"}


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
        async with aiohttp.ClientSession() as session:
            models_url = "http://{}:{}/v1/models".format(host, port)
            data = {"program_code": program_code}
            async with session.post(models_url, data=json.dumps(data), headers=headers) as resp:
                assert resp.status == 201
                model_name = (await resp.json())["name"]

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
