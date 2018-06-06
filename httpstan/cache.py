"""Cache management.

Functions in this module manage the Stan model cache and related caches.
"""
import asyncio
import logging
import lzma
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
    # create tables if they do not exist
    conn.execute(
        """PRAGMA journal_mode=WAL;"""
    )  # use write-ahead-log, available since sqlite 3.7.0
    with conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS models (key BLOB PRIMARY KEY, value BLOB);""")
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


async def dump_model_extension_module(model_id: str, module_bytes: bytes, db: sqlite3.Connection):
    """Store Stan model extension module the cache.

    The Stan model extension module is passed via ``module_bytes``. The bytes
    will be compressed before writing to the cache.

    Since compressing the bytes will take time, the compression function is run
    in a different thread.

    This function is a coroutine.

    Arguments:
        model_id: Stan model id
        module_bytes: Bytes of the compile Stan model extension module.
        db: Cache database handle.

    """
    compressed = await asyncio.get_event_loop().run_in_executor(None, lzma.compress, module_bytes)
    with db:
        db.execute("""INSERT INTO models VALUES (?, ?)""", (model_id.encode(), compressed))


async def load_model_extension_module(model_id: str, db: sqlite3.Connection) -> bytes:
    """Load Stan model extension module the cache.

    The extension module is stored in compressed form. Since decompressing the
    module will take time, the decompression function is run in a different
    thread.

    This function is a coroutine.

    Arguments:
        model_id: Stan model id
        db: Cache database handle.

    Returns
        bytes: Bytes of compiled extension module.

    """
    row = db.execute("""SELECT value FROM models WHERE key=?""", (model_id.encode(),)).fetchone()
    if not row:
        raise KeyError(f"Extension module for id `{model_id}` not found.")
    compressed = row[0]
    return await asyncio.get_event_loop().run_in_executor(None, lzma.decompress, compressed)
