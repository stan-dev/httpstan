"""Cache management.

Functions in this module manage the Stan model cache and related caches.
"""
import logging
import shutil
import typing
from importlib.machinery import EXTENSION_SUFFIXES
from pathlib import Path

import appdirs

import httpstan

logger = logging.getLogger("httpstan")


def cache_directory() -> Path:
    """Get httpstan cache path."""
    return Path(appdirs.user_cache_dir("httpstan", version=httpstan.__version__))


def model_directory(model_name: str) -> Path:
    """Get the path to a model's directory. Directory may not exist."""
    model_id = model_name.split("/")[1]
    return cache_directory() / "models" / model_id


def fit_path(fit_name: str) -> Path:
    """Get the path to a fit file. File may not exist."""
    # fit_name structure: cache / models / model_id / fit_id
    fit_directory, fit_id = fit_name.rsplit("/", maxsplit=1)
    fit_filename = fit_id + ".jsonlines.gz"
    return cache_directory() / fit_directory / fit_filename


def delete_model_directory(model_name: str) -> None:
    """Delete the directory in which a model and associated fits are stored."""
    shutil.rmtree(model_directory(model_name), ignore_errors=True)


def dump_services_extension_module_compiler_output(compiler_output: str, model_name: str) -> None:
    """Dump compiler output from building a model-specific stan::services extension module."""
    model_directory_ = model_directory(model_name)
    model_directory_.mkdir(parents=True, exist_ok=True)
    with (model_directory_ / "stderr.log").open("w") as fh:
        fh.write(compiler_output)


def load_services_extension_module_compiler_output(model_name: str) -> str:
    """Load compiler output from building a model-specific stan::services extension module."""
    # may raise KeyError
    model_directory_ = model_directory(model_name)
    if not model_directory_.exists():
        raise KeyError(f"Directory for `{model_name}` at `{model_directory}` does not exist.")
    with (model_directory_ / "stderr.log").open() as fh:
        return fh.read()


def list_model_names() -> typing.List[str]:
    """Return model names (e.g., `models/dyeicfn2`) for models in cache."""
    models_directory = cache_directory() / "models"
    if not models_directory.exists():
        return []

    def has_extension_suffix(path: Path) -> bool:
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
    model_directory_ = model_directory(model_name)
    model_directory_.mkdir(parents=True, exist_ok=True)
    with (model_directory_ / "stanc.log").open("w") as fh:
        fh.write(stanc_warnings)


def load_stanc_warnings(model_name: str) -> str:
    """Load stanc output associated with a model."""
    # may raise KeyError
    model_directory_ = model_directory(model_name)
    if not model_directory_.exists():
        raise KeyError(f"Directory for `{model_name}` at `{model_directory}` does not exist.")
    with (model_directory_ / "stanc.log").open() as fh:
        return fh.read()


def dump_fit(fit_bytes: bytes, name: str) -> None:
    """Store Stan fit in filesystem-based cache.

    The Stan fit is passed via ``fit_bytes``. The content
    must already be compressed.

    Arguments:
        name: Stan fit name
        fit_bytes: gzip-compressed messages associated with Stan fit.
    """
    # fits are stored under their "parent" models
    path = fit_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        fh.write(fit_bytes)


def load_fit(name: str) -> bytes:
    """Load Stan fit from the filesystem-based cache.

    Arguments:
        name: Stan fit name
        model_name: Stan model name

    Returns
        gzip-compressed messages associated with Stan fit.
    """
    # fits are stored under their "parent" models
    path = fit_path(name)
    try:
        with path.open("rb") as fh:
            return fh.read()
    except FileNotFoundError:
        raise KeyError(f"Fit `{name}` not found.")


def delete_fit(name: str) -> None:
    """Delete Stan fit from the filesystem-based cache.

    Arguments:
        name: Stan fit name
    """
    path = fit_path(name)
    try:
        path.unlink()
    except FileNotFoundError:
        raise KeyError(f"Fit `{name}` not found.")
