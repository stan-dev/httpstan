"""Test services function argument lookups."""
import pathlib

import httpstan.app
import httpstan.cache


def test_model_directory() -> None:
    model_name = "models/abcdef"
    model_directory = httpstan.cache.model_directory(model_name)
    model_dirpath = pathlib.Path(model_directory)
    assert model_dirpath.name == "abcdef"
