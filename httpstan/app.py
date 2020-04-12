"""Helper function to launch httpstan server.

Configure the server and schedule startup and shutdown tasks.
"""
import asyncio
import logging

import aiohttp.web

import httpstan.routes

try:
    from uvloop import EventLoopPolicy
except ImportError:
    EventLoopPolicy = asyncio.DefaultEventLoopPolicy


logger = logging.getLogger("httpstan")


async def _warn_unfinished_operations(app: aiohttp.web.Application) -> None:
    """Warn if tasks (e.g., operations) are unfinished.

    Called immediately before tasks are cancelled.

    """
    # Note: Python 3.7 and later use `asyncio.all_tasks`.
    for operation_name in app["operations"]:
        op = await httpstan.cache.load_operation(operation_name, app["db"])
        if not op["done"]:
            logger.critical(f'Operation `{op["name"]}` cancelled before finishing.')


def make_app() -> aiohttp.web.Application:
    """Assemble aiohttp Application.

    Returns:
        aiohttp.web.Application: assembled aiohttp application.

    """
    app = aiohttp.web.Application()
    httpstan.routes.setup_routes(app)
    # startup and shutdown tasks
    app.on_startup.append(httpstan.cache.init_cache)
    app["operations"] = set()
    app.on_cleanup.append(_warn_unfinished_operations)
    app.on_cleanup.append(httpstan.cache.close_cache)
    return app
