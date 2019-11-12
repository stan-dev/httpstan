"""Test services function argument lookups."""

import pytest

import httpstan.cache
import httpstan.models
import httpstan.services.arguments as arguments
import helpers

program_code = "parameters {real y;} model {y ~ normal(0,1);}"


def test_lookup_default() -> None:
    """Test argument default value lookup."""
    assert 1000 == arguments.lookup_default(arguments.Method.SAMPLE, "num_samples")
    assert 0.05 == arguments.lookup_default(arguments.Method.SAMPLE, "gamma")


@pytest.mark.asyncio
async def test_function_arguments(api_url: str) -> None:
    """Test function argument name lookup."""

    # function_arguments needs compiled module, so we have to get one
    model_name = await helpers.get_model_name(api_url, program_code)

    # get a reference to the model_module
    app: dict = {}  # mock aiohttp.web.Application
    # the following call sets up database, populates app['db']
    await httpstan.cache.init_cache(app)  # type: ignore
    module_bytes, compiler_output = await httpstan.cache.load_model_extension_module(
        model_name, app["db"]
    )
    assert module_bytes is not None
    assert compiler_output is not None
    model_module = httpstan.models.import_model_extension_module(model_name, module_bytes)

    expected = [
        "data",
        "init",
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
        "delta",
        "gamma",
        "kappa",
        "t0",
        "init_buffer",
        "term_buffer",
        "window",
    ]

    assert expected == arguments.function_arguments("hmc_nuts_diag_e_adapt", model_module)
