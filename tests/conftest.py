"""pytest configuration for all tests."""
import aiohttp.web
import asyncio
import typing
import threading

import pytest

import httpstan.app


@pytest.fixture
def server_host_port_pair(
    unused_tcp_port: int,
) -> typing.Generator[typing.Tuple[str, int], None, None]:
    """Arrange event loop with httpstan server running.

    HTTP server shutdown is handled as well.
    """
    host, port = "127.0.0.1", unused_tcp_port
    app = httpstan.app.make_app()
    runner = aiohttp.web.AppRunner(app)
    # After dropping Python 3.6, use `asyncio.run`
    asyncio.get_event_loop().run_until_complete(runner.setup())
    site = aiohttp.web.TCPSite(runner, host, port)
    # After dropping Python 3.6, use `asyncio.run`
    asyncio.get_event_loop().run_until_complete(site.start())
    # After dropping Python 3.6, use `get_running_loop`
    loop = asyncio.get_event_loop()
    t = threading.Thread(target=loop.run_forever)
    # after this call, the event loop is running in thread which is not the main
    # thread. All interactions with the event loop must use thread-safe calls
    t.start()
    yield (host, port)
    asyncio.run_coroutine_threadsafe(runner.cleanup(), loop)
    loop.call_soon_threadsafe(loop.stop)  # stops `run_forever`
    t.join(timeout=1)


@pytest.fixture
def api_url(server_host_port_pair: typing.Tuple[str, int]) -> str:
    host, port = server_host_port_pair
    return f"http://{host}:{port}/v1"
