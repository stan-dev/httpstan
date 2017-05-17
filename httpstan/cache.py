"""Cache management.

Functions in this module manage the Stan Program cache and related caches.
"""
import asyncio
import logging
import lzma
import os

import appdirs
import lmdb


logger = logging.getLogger('httpstan')
HTTPSTAN_LMDB_MAP_SIZE = os.environ.get('HTTPSTAN_LMDB_MAP_SIZE', 1024 ** 3)


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
    cache_path = appdirs.user_cache_dir('httpstan')
    logging.info(f'Opening cache in `{cache_path}`.')
    db = lmdb.Environment(cache_path, map_size=HTTPSTAN_LMDB_MAP_SIZE)
    app['db'] = db


async def close_cache(app):
    """Close cache.

    This function is intended to be added to the ``on_cleanup`` functions
    associated with an ``aiohttp.web.Application``.

    This function is a coroutine.

    Arguments:
        app (aiohttp.web.Application): The current application.

    """
    logging.info('Closing cache.')
    app['db'].close()


async def dump_program_extension_module(program_id: str, module_bytes: bytes, db: lmdb.Environment):
    """Store Stan Program extension module the cache.

    The Stan Program extension module is passed via ``module_bytes``. The bytes
    will be compressed before writing to the cache.

    Since compressing the bytes will take time, the compression function is run
    in a different thread.

    This function is a coroutine.

    Arguments:
        program_id: Stan Program id
        module_bytes: Bytes of the compile Stan Program extension module.
        db: Cache database handle.

    """
    compressed = await asyncio.get_event_loop().run_in_executor(None, lzma.compress, module_bytes)
    with db.begin(write=True) as txn:
        txn.put(program_id.encode(), compressed)


async def load_program_extension_module(program_id: str, db: lmdb.Environment) -> bytes:
    """Load Stan Program extension module the cache.

    The extension module is stored in compressed form. Since decompressing the
    module will take time, the decompression function is run in a different
    thread.

    This function is a coroutine.

    Arguments:
        program_id: Stan Program id
        db: Cache database handle.

    Returns
        bytes: Bytes of compiled extension module.

    """
    with db.begin(write=False) as txn:
        compressed = txn.get(program_id.encode())
    if compressed is None:
        raise ValueError(f'Extension module for id `{program_id}` not found.')
    return await asyncio.get_event_loop().run_in_executor(None, lzma.decompress, compressed)
