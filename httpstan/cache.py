"""Cache management.

Functions in this module manage the Stan model cache and related caches.
"""
import asyncio
import gzip
import json
import logging
import os
import sqlite3
from typing import Tuple

import appdirs

import httpstan

logger = logging.getLogger("httpstan")


async def init_cache(app):
    """Store reference to opened cache database in app.

    Objects stored in the aiohttp.web.Application instance can be accessed by
    all request handlers.

    This function is intended to be added to the ``on_startup`` functions
    associated with an ``aiohttp.web.Application``.

    This function is a coroutine.

    Arguments:
        app (aiohttp.web.Application): The current application.

    """
    cache_path = appdirs.user_cache_dir("httpstan", version=httpstan.__version__)
    os.makedirs(cache_path, exist_ok=True)
    logging.info(f"Opening cache in `{cache_path}`.")
    # if `check_same_thread` is False, use of `conn` across threads should work
    conn = sqlite3.connect(os.path.join(cache_path, "cache.sqlite3"), check_same_thread=False)
    # use write-ahead-log, available since sqlite 3.7.0
    conn.execute("""PRAGMA journal_mode=WAL;""")
    with conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS fits (name BLOB PRIMARY KEY, model_name BLOB, value BLOB);"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS models (name BLOB PRIMARY KEY, value BLOB, compiler_output TEXT);"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS operations (name BLOB PRIMARY KEY, value value BLOB);"""
        )
    app["db"] = conn


async def close_cache(app):
    """Close cache.

    This function is intended to be added to the ``on_cleanup`` functions
    associated with an ``aiohttp.web.Application``.

    This function is a coroutine.

    Arguments:
        app (aiohttp.web.Application): The current application.

    """
    logging.info("Closing cache.")
    app["db"].close()


async def dump_model_extension_module(
    model_name: str, module_bytes: bytes, compiler_output: str, db: sqlite3.Connection
):
    """Store Stan model extension module the cache.

    The Stan model extension module is passed via ``module_bytes``. The bytes
    will be compressed before writing to the cache.

    Since compressing the bytes will take time, the compression function is run
    in a different thread.

    This function is a coroutine.

    Arguments:
        model_name: Model name.
        module_bytes: Bytes of the compile Stan model extension module.
        compiler_output: Output (standard error) from compiler.
        db: Cache database handle.

    """
    compress_level = 1  # fastest
    compressed = await asyncio.get_event_loop().run_in_executor(
        None, gzip.compress, module_bytes, compress_level
    )
    with db:
        db.execute(
            """INSERT INTO models VALUES (?, ?, ?)""",
            (model_name.encode(), compressed, compiler_output.encode()),
        )


async def load_model_extension_module(model_name: str, db: sqlite3.Connection) -> Tuple[bytes, str]:
    """Load Stan model extension module the cache.

    The extension module is stored in compressed form. Since decompressing the
    module will take time, the decompression function is run in a different
    thread.

    This function is a coroutine.

    Arguments:
        model_name: Model name
        db: Cache database handle.

    Returns
        bytes: Bytes of compiled extension module.
        str: Output (standard error) from compiler.

    """
    row = db.execute(
        """SELECT value, compiler_output FROM models WHERE name=?""", (model_name.encode(),)
    ).fetchone()
    if not row:
        raise KeyError(f"Extension module for `{model_name}` not found.")
    compressed, compiler_output = row
    module_bytes = await asyncio.get_event_loop().run_in_executor(None, gzip.decompress, compressed)
    return module_bytes, compiler_output


async def dump_fit(name: str, fit_bytes: bytes):
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


async def dump_operation(name: str, value: bytes, db: sqlite3.Connection):
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
    """Load serialized Operation.

    This function is a coroutine.

    Arguments:
        name: Operation name.
        db: Cache database handle.

    """
    row = db.execute("""SELECT value FROM operations WHERE name=?""", (name.encode(),)).fetchone()
    if not row:
        raise KeyError(f"Operation `{name}` not found.")
    (value,) = row
    return json.loads(value.decode())
