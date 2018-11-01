"""Cache management.

Functions in this module manage the Stan model cache and related caches.
"""
import asyncio
import gzip
import logging
import os
import sqlite3

import appdirs

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
    cache_path = appdirs.user_cache_dir("httpstan")
    os.makedirs(cache_path, exist_ok=True)
    logging.info(f"Opening cache in `{cache_path}`.")
    # if `check_same_thread` is False, use of `conn` across threads should work
    conn = sqlite3.connect(os.path.join(cache_path, "cache.sqlite3"), check_same_thread=False)
    # use write-ahead-log, available since sqlite 3.7.0
    conn.execute("""PRAGMA journal_mode=WAL;""")
    with conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS fits (name BLOB PRIMARY KEY, model_name BOB, value BLOB);"""
        )
        conn.execute("""CREATE TABLE IF NOT EXISTS models (key BLOB PRIMARY KEY, value BLOB);""")
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


async def dump_model_extension_module(model_name: str, module_bytes: bytes, db: sqlite3.Connection):
    """Store Stan model extension module the cache.

    The Stan model extension module is passed via ``module_bytes``. The bytes
    will be compressed before writing to the cache.

    Since compressing the bytes will take time, the compression function is run
    in a different thread.

    This function is a coroutine.

    Arguments:
        model_name: Model name
        module_bytes: Bytes of the compile Stan model extension module.
        db: Cache database handle.

    """
    compress_level = 1  # fastest
    compressed = await asyncio.get_event_loop().run_in_executor(
        None, gzip.compress, module_bytes, compress_level
    )
    with db:
        db.execute("""INSERT INTO models VALUES (?, ?)""", (model_name.encode(), compressed))


async def load_model_extension_module(model_name: str, db: sqlite3.Connection) -> bytes:
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

    """
    row = db.execute("""SELECT value FROM models WHERE key=?""", (model_name.encode(),)).fetchone()
    if not row:
        raise KeyError(f"Extension module for `{model_name}` not found.")
    compressed = row[0]
    return await asyncio.get_event_loop().run_in_executor(None, gzip.decompress, compressed)


async def dump_fit(name: str, fit_bytes: bytes, model_name: str, db: sqlite3.Connection):
    """Store Stan fit in the cache.

    The Stan fit is passed via ``fit_bytes``. ``model_name`` must also be provided
    as a rudimentary integrity check.

    Since compressing the bytes will take time, the compression function is run
    in a different thread.

    This function is a coroutine.

    Arguments:
        name: Stan fit name
        fit_bytes: Bytes of the Stan fit.
        model_name: Name of Stan model associated with fit.
        db: Cache database handle.

    """
    with db:
        db.execute(
            """INSERT INTO fits VALUES (?, ?, ?)""", (name.encode(), model_name.encode(), fit_bytes)
        )


async def load_fit(name: str, model_name: str, db: sqlite3.Connection) -> bytes:
    """Load Stan fit from the cache.

    Model id must also be provided as a rudimentary integrity check. (Every
    fit is associated with a unique model.)

    This function is a coroutine.

    Arguments:
        name: Stan fit name
        model_name: Stan model name
        db: Cache database handle.

    Returns
        bytes: Bytes of fit.

    """
    row = db.execute(
        """SELECT model_name, value FROM fits WHERE name=?""", (name.encode(),)
    ).fetchone()
    if not row:
        raise KeyError(f"Fit `{name}` not found.")
    model_name_db, fit_bytes = row
    if model_name != model_name_db.decode():
        raise KeyError(
            f"Unexpected model when loading saved fit. Expected `{model_name}`, found `{model_name_db.decode()}`."
        )
    return fit_bytes
