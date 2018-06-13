"""Configure httpstan server.

Configure the server and schedule startup and shutdown tasks.
"""
import asyncio
import logging
import threading

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


class Server(threading.Thread):
    """Manage starting and stopping the web application.

    This wraps some of the complexity of starting and stopping an aiohttp
    application in another thread.

    Note that the HTTP server takes a fraction of a second to start. Consider checking
    for availability or waiting a tenth of a second before making calls.

    """

    def __init__(
        self, host: str = "127.0.0.1", port: int = 8080, loop: asyncio.AbstractEventLoop = None
    ) -> None:
        super().__init__()
        self.host, self.port = host, port
        self.loop = asyncio.get_event_loop() if loop is None else loop
        self.runner = None

    def run(self):
        """Runs in a separate thread when ``start`` is called."""
        # This thread takes over control of the event loop.
        asyncio.set_event_loop(self.loop)
        app = make_app(self.loop)

        self.runner = aiohttp.web.AppRunner(app)
        self.loop.run_until_complete(self.runner.setup())
        site = aiohttp.web.TCPSite(self.runner, self.host, self.port)
        self.loop.run_until_complete(site.start())

        self.loop.run_forever()  # will stop when ``stop`` is called

    def stop(self):
        """Arrange for the server to gracefully exit."""
        if not self.is_alive():
            raise RuntimeError("httpstan Server thread is not alive.")
        asyncio.run_coroutine_threadsafe(self.runner.cleanup(), self.loop)
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.join()
