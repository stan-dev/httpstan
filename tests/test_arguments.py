"""Test services function argument lookups."""

from typing import Any, Tuple

import pytest

import helpers
import httpstan.app
import httpstan.models
import httpstan.services.arguments as arguments

program_code = "parameters {real y;} model {y ~ normal(0,1);}"


@pytest.mark.parametrize("argument_value", [("num_samples", 1000), ("gamma", 0.05)])
def test_lookup_default(argument_value: Tuple[str, Any]) -> None:
    """Test argument default value lookup."""
    arg, value = argument_value
    assert value == arguments.lookup_default(arguments.Method.SAMPLE, arg)


def test_lookup_invalid() -> None:
    """Test argument default value lookup with invalid argument."""
    with pytest.raises(ValueError, match=r"No argument `.*` is associated with `.*`\."):
        arguments.lookup_default(arguments.Method.SAMPLE, "invalid_argument")


@pytest.mark.asyncio
async def test_function_arguments(api_url: str) -> None:
    """Test function argument name lookup."""

    # function_arguments needs compiled module, so we have to get one
    model_name = await helpers.get_model_name(api_url, program_code)

    # get a reference to the model-specific services extension module
    # the following call sets up database, populates app['db']
    module = httpstan.models.import_services_extension_module(model_name)

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

    assert expected == arguments.function_arguments("hmc_nuts_diag_e_adapt", module)


@pytest.mark.parametrize(
    "type_pair", [("double", float), ("int", int), ("unsigned int", int), ("bool", bool), ("string", str)]
)
def test_pythonize_cmdstan_type(type_pair: Tuple[str, Any]) -> None:
    """Test pythonization of the cmdstan types."""
    cmdstan_type, python_type = type_pair
    assert arguments._pythonize_cmdstan_type(cmdstan_type) == python_type


@pytest.mark.parametrize("type_fail", [("list element", NotImplementedError), ("invalid type", ValueError)])
def test_pythonize_cmdstan_type_invalid(type_fail: Tuple[str, Any]) -> None:
    cmdstan_type, error = type_fail
    with pytest.raises(error, match=r"Cannot convert CmdStan `.*` to Python type\."):
        arguments._pythonize_cmdstan_type(cmdstan_type)
