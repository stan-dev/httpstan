"""Cache management.

Functions in this module manage the Stan model cache and related caches.
"""
import json
import logging
import os
import pathlib
import sqlite3
from typing import cast

import aiohttp.web
import appdirs

import httpstan

logger = logging.getLogger("httpstan")


def cache_db_filename() -> str:
    cache_path = appdirs.user_cache_dir("httpstan", version=httpstan.__version__)
    return os.path.join(cache_path, "cache.sqlite3")


def model_directory(model_name: str) -> str:
    """Get the path to a model's directory. Directory may not exist."""
    cache_path = appdirs.user_cache_dir("httpstan", version=httpstan.__version__)
    model_id = model_name.split("/")[1]
    return os.path.join(cache_path, "models", model_id)


def services_extension_module_compiler_output(model_name: str) -> str:
    """Load compiler output from building a model-specific stan::services extension module."""
    # may raise KeyError
    model_directory_ = pathlib.Path(model_directory(model_name))
    if not model_directory_.exists():
        raise KeyError(f"Directory for `{model_name}` at `{model_directory}` does not exist.")
    with open(model_directory_ / "stderr.log") as fh:
        return fh.read()


async def init_cache(app: aiohttp.web.Application) -> None:
    """Store reference to opened cache database in app.

    Objects stored in the aiohttp.web.Application instance can be accessed by
    all request handlers.

    This function is intended to be added to the ``on_startup`` functions
    associated with an ``aiohttp.web.Application``.

    This function is a coroutine.

    Arguments:
        app (aiohttp.web.Application): The current application.

    """
    cache_db_filename_ = cache_db_filename()
    os.makedirs(os.path.dirname(cache_db_filename_), exist_ok=True)
    logging.info(f"Using sqlite3 database `{cache_db_filename_}` to store pending operation info.")
    # if `check_same_thread` is False, use of `conn` across threads should work
    conn = sqlite3.connect(cache_db_filename_, check_same_thread=False)
    with conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS operations (name BLOB PRIMARY KEY, value value BLOB);""")
    app["db"] = conn


async def close_cache(app: aiohttp.web.Application) -> None:
    """Close cache.

    This function is intended to be added to the ``on_cleanup`` functions
    associated with an ``aiohttp.web.Application``.

    This function is a coroutine.

    Arguments:
        app (aiohttp.web.Application): The current application.

    """
    logging.info("Closing cache.")
    app["db"].close()


async def dump_fit(name: str, fit_bytes: bytes) -> None:
    """Store Stan fit in filesystem-based cache.

    The Stan fit is passed via ``fit_bytes``.

    This function is a coroutine.

    Arguments:
        name: Stan fit name
        fit_bytes: Bytes of the Stan fit.

    """
    cache_path = appdirs.user_cache_dir("httpstan", version=httpstan.__version__)
    # fits are stored under their "parent" models
    fit_path = os.path.join(*([cache_path] + name.split("/")[:-1]))
    fit_filename = os.path.join(fit_path, f'{name.split("/")[-1]}.dat')
    os.makedirs(fit_path, exist_ok=True)
    with open(fit_filename, "wb") as fh:
        fh.write(fit_bytes)


async def load_fit(name: str) -> bytes:
    """Load Stan fit from the filesystem-based cache.

    This function is a coroutine.

    Arguments:
        name: Stan fit name
        model_name: Stan model name

    Returns
        bytes: Bytes of fit.

    """
    cache_path = appdirs.user_cache_dir("httpstan", version=httpstan.__version__)
    # fits are stored under their "parent" models
    fit_path = os.path.join(*([cache_path] + name.split("/")[:-1]))
    fit_filename = os.path.join(fit_path, f'{name.split("/")[-1]}.dat')
    try:
        with open(fit_filename, "rb") as fh:
            return fh.read()
    except FileNotFoundError:
        raise KeyError(f"Fit `{name}` not found.")


async def dump_operation(name: str, value: bytes, db: sqlite3.Connection) -> None:
    """Store serialized Operation in cache.

    This function is a coroutine.

    Arguments:
        name: Operation name.
        value: Operation, serialized as JSON.
        db: Cache database handle.

    """
    with db:
        db.execute("""INSERT OR REPLACE INTO operations VALUES (?, ?)""", (name.encode(), value))


async def load_operation(name: str, db: sqlite3.Connection) -> dict:
    """Load serialized Operation from the cache database.

    This function is a coroutine.

    Arguments:
        name: Operation name.
        db: Cache database handle.

    """
    row = db.execute("""SELECT value FROM operations WHERE name=?""", (name.encode(),)).fetchone()
    if not row:
        raise KeyError(f"Operation `{name}` not found.")
    (value,) = row
    return cast(dict, json.loads(value.decode()))
