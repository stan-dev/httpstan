"""Cache management.

Functions in this module manage the Stan model cache and related caches.
"""
import logging
import os
import pathlib
import shutil
import typing
from importlib.machinery import EXTENSION_SUFFIXES

import appdirs

import httpstan

logger = logging.getLogger("httpstan")


def model_directory(model_name: str) -> str:
    """Get the path to a model's directory. Directory may not exist."""
    cache_path = appdirs.user_cache_dir("httpstan", version=httpstan.__version__)
    model_id = model_name.split("/")[1]
    return os.path.join(cache_path, "models", model_id)


def delete_model_directory(model_name: str) -> None:
    """Delete the directory in which a model and associated fits are stored."""
    shutil.rmtree(model_directory(model_name), ignore_errors=True)


def dump_services_extension_module_compiler_output(compiler_output: str, model_name: str) -> None:
    """Dump compiler output from building a model-specific stan::services extension module."""
    model_directory_ = pathlib.Path(model_directory(model_name))
    model_directory_.mkdir(parents=True, exist_ok=True)
    with open(model_directory_ / "stderr.log", "w") as fh:
        fh.write(compiler_output)


def load_services_extension_module_compiler_output(model_name: str) -> str:
    """Load compiler output from building a model-specific stan::services extension module."""
    # may raise KeyError
    model_directory_ = pathlib.Path(model_directory(model_name))
    if not model_directory_.exists():
        raise KeyError(f"Directory for `{model_name}` at `{model_directory}` does not exist.")
    with open(model_directory_ / "stderr.log") as fh:
        return fh.read()


def list_model_names() -> typing.List[str]:
    """Return model names (e.g., `models/dyeicfn2`) for models in cache."""
    cache_path = appdirs.user_cache_dir("httpstan", version=httpstan.__version__)
    models_directory = pathlib.Path(os.path.join(cache_path, "models"))
    if not models_directory.exists():
        return []

    def has_extension_suffix(path: pathlib.Path) -> bool:
        return path.suffix in EXTENSION_SUFFIXES

    model_names = []
    for item in models_directory.iterdir():
        if not item.is_dir():
            continue
        # look for a compiled extension module, file with a suffix in EXTENSION_SUFFIXES
        if any(map(has_extension_suffix, item.iterdir())):
            model_names.append(f"models/{item.name}")
    return model_names


def dump_stanc_warnings(stanc_warnings: str, model_name: str) -> None:
    """Dump stanc warnings associated with a model."""
    model_directory_ = pathlib.Path(model_directory(model_name))
    model_directory_.mkdir(parents=True, exist_ok=True)
    with open(model_directory_ / "stanc.log", "w") as fh:
        fh.write(stanc_warnings)


def load_stanc_warnings(model_name: str) -> str:
    """Load stanc output associated with a model."""
    # may raise KeyError
    model_directory_ = pathlib.Path(model_directory(model_name))
    if not model_directory_.exists():
        raise KeyError(f"Directory for `{model_name}` at `{model_directory}` does not exist.")
    with open(model_directory_ / "stanc.log") as fh:
        return fh.read()


def dump_fit(fit_bytes: bytes, name: str) -> None:
    """Store Stan fit in filesystem-based cache.

    The Stan fit is passed via ``fit_bytes``. The content
    must already be compressed.

    Arguments:
        name: Stan fit name
        fit_bytes: LZ4-compressed messages associated with Stan fit.
    """
    cache_path = appdirs.user_cache_dir("httpstan", version=httpstan.__version__)
    # fits are stored under their "parent" models
    fits_path = os.path.join(*([cache_path] + name.split("/")[:-1]))
    fit_filename = os.path.join(fits_path, f'{name.split("/")[-1]}.jsonlines.lz4')
    os.makedirs(fits_path, exist_ok=True)
    with open(fit_filename, mode="wb") as fh:
        fh.write(fit_bytes)


def load_fit(name: str) -> bytes:
    """Load Stan fit from the filesystem-based cache.

    Arguments:
        name: Stan fit name
        model_name: Stan model name

    Returns
        LZ4-compressed messages associated with Stan fit.
    """
    cache_path = appdirs.user_cache_dir("httpstan", version=httpstan.__version__)
    # fits are stored under their "parent" models
    fits_path = os.path.join(*([cache_path] + name.split("/")[:-1]))
    fit_filename = os.path.join(fits_path, f'{name.split("/")[-1]}.jsonlines.lz4')
    try:
        with open(fit_filename, mode="rb") as fh:
            return fh.read()
    except FileNotFoundError:
        raise KeyError(f"Fit `{name}` not found.")


def delete_fit(name: str) -> None:
    """Delete Stan fit from the filesystem-based cache.

    Arguments:
        name: Stan fit name
    """
    cache_path = appdirs.user_cache_dir("httpstan", version=httpstan.__version__)
    fits_path = os.path.join(*([cache_path] + name.split("/")[:-1]))
    fit_id = name.split("/")[-1]
    pathlib.Path(os.path.join(fits_path, f"{fit_id}.jsonlines.lz4")).unlink()
