"""Test services function argument lookups."""
import pathlib

import pytest

import httpstan.app
import httpstan.cache


@pytest.mark.asyncio
async def test_unknown_op_cache(api_url: str) -> None:
    """Test function argument name lookup."""
    app = httpstan.app.make_app()
    await httpstan.cache.init_cache(app)
    with pytest.raises(KeyError, match=r"Operation `.*` not found\."):
        await httpstan.cache.load_operation("unknown_op", app["db"])


def test_model_directory() -> None:
    model_name = "models/abcdef"
    model_directory = httpstan.cache.model_directory(model_name)
    model_dirpath = pathlib.Path(model_directory)
    assert model_dirpath.name == "abcdef"
