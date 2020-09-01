"""pytest configuration for all tests."""
import typing

import aiohttp.web
import pytest

import httpstan.app


@pytest.fixture
async def server_host_port_pair(
    unused_tcp_port: int,
) -> typing.AsyncGenerator[typing.Tuple[str, int], None]:
    """Arrange event loop with httpstan server running.

    HTTP server shutdown is handled as well.
    """
    host, port = "127.0.0.1", unused_tcp_port
    app = httpstan.app.make_app()
    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = aiohttp.web.TCPSite(runner, host, port)
    await site.start()
    yield (host, port)
    await runner.cleanup()


@pytest.fixture
async def api_url(server_host_port_pair: typing.Tuple[str, int]) -> str:
    host, port = server_host_port_pair
    return f"http://{host}:{port}/v1"
