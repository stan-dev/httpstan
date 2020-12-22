"""Test services function argument lookups."""
import pytest

import httpstan.app
import httpstan.cache
import httpstan.models

import helpers


def test_model_directory() -> None:
    model_name = "models/abcdef"
    model_directory = httpstan.cache.model_directory(model_name)
    assert model_directory.name == "abcdef"


def test_fit_path() -> None:
    fit_name = "models/abcdef/ghijklmn"
    path = httpstan.cache.fit_path(fit_name)
    assert path.name == "ghijklmn.jsonlines.lz4"


@pytest.mark.asyncio
async def test_list_model_names(api_url: str) -> None:
    program_code = "parameters {real y;} model {y ~ normal(0,1);}"
    model_name = httpstan.models.calculate_model_name(program_code)
    payload = {"function": "stan::services::sample::hmc_nuts_diag_e_adapt"}
    operation = await helpers.sample(api_url, program_code, payload)
    assert operation
    model_names = httpstan.cache.list_model_names()
    assert len(model_names) > 0 and model_name in model_names


def load_services_extension_module_compiler_output_exception() -> None:
    model_name = "models/abcdefghijklmnopqrs"  # does not exist
    with pytest.raises(KeyError):
        httpstan.cache.load_services_extension_module_compiler_output(model_name)


def load_stanc_warnings_exception() -> None:
    model_name = "models/abcdefghijklmnopqrs"  # does not exist
    with pytest.raises(KeyError):
        httpstan.cache.load_stanc_warnings(model_name)


def list_model_names() -> None:
    model_names = httpstan.cache.list_model_names()
    assert isinstance(model_names, list)
    assert all(name.startswith("models/") for name in model_names)
