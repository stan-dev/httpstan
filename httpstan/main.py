"""Configure httpstan server.

Configure the server and schedule startup and shutdown tasks.
"""
import asyncio
import logging
import threading
from typing import Optional

import aiohttp.web
import uvloop

import httpstan.routes

logger = logging.getLogger("httpstan")


async def _warn_unfinished_operations(app):
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


class Server(threading.Thread):
    """Manage starting and stopping the web application.

    This wraps some of the complexity of starting and stopping an aiohttp
    application in another thread.

    Note that the HTTP server takes a fraction of a second to start. Consider checking
    for availability or waiting a tenth of a second before making calls.

    """

    def __init__(self, host: str = "127.0.0.1", port: Optional[int] = None) -> None:
        super().__init__()
        self.host, self.port = host, port
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        self.loop = asyncio.new_event_loop()  # control will be passed to thread
        self.app = make_app()
        self.runner = aiohttp.web.AppRunner(self.app)
        self.loop.run_until_complete(self.runner.setup())

        # if `port` is None, search for an available port
        if self.port is None:
            for port in range(8080, 9000):
                try:
                    site = aiohttp.web.TCPSite(self.runner, self.host, port)
                    self.loop.run_until_complete(site.start())
                except OSError:
                    continue
                else:
                    self.port = port
                    break
            else:
                raise RuntimeError(f"Unable to find an available port with host `{self.host}`.")
        else:
            site = aiohttp.web.TCPSite(self.runner, self.host, self.port)
            self.loop.run_until_complete(site.start())

    def run(self):
        """Runs in a separate thread when ``start`` is called."""
        # This thread takes over control of the event loop.
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()  # will stop when ``stop`` is called

    def stop(self):
        """Arrange for the server to gracefully exit."""
        # reminder: these functions are called from the original context
        if not self.is_alive():
            raise RuntimeError("httpstan Server thread is not alive.")
        # self.loop is controlled by another thread
        # future is a concurrent.futures.Future
        future = asyncio.run_coroutine_threadsafe(self.runner.cleanup(), self.loop)
        future.result(1)
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.join()
