"""pytest configuration for all tests."""
import asyncio

import aiohttp
import pytest

import httpstan.main


@pytest.fixture(scope="session")
def host():
    """Host for server to listen on."""
    return "127.0.0.1"


@pytest.fixture(scope="session")
def port():
    """Port for server to listen on."""
    return 8080


@pytest.fixture(scope="module")
def loop_with_server(request, host, port):
    """Return event loop with httpstan server already running.

    HTTP server shutdown is handled as well.
    """
    l = asyncio.new_event_loop()
    asyncio.set_event_loop(None)

    # setup server
    app = httpstan.main.make_app(l)
    runner = aiohttp.web.AppRunner(app)
    l.run_until_complete(runner.setup())
    site = aiohttp.web.TCPSite(runner, "localhost", 8080)
    l.run_until_complete(site.start())

    yield l  # yield control, test proper would start here

    l.run_until_complete(runner.cleanup())
    l.close()
