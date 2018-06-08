"""Configure httpstan server.

Configure the server and schedule startup and shutdown tasks.
"""
import asyncio
import logging

import aiohttp.web

import httpstan.routes


logger = logging.getLogger("httpstan")


def make_app(loop: asyncio.AbstractEventLoop) -> aiohttp.web.Application:
    """Assemble aiohttp Application.

    Arguments:
        loop: event loop.

    Returns:
        aiohttp.web.Application: assembled aiohttp application.

    """
    app = aiohttp.web.Application()
    httpstan.routes.setup_routes(app)
    # startup and shutdown tasks
    app.on_startup.append(httpstan.cache.init_cache)
    app.on_cleanup.append(httpstan.cache.close_cache)
    return app
