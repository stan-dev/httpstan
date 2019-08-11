"""pytest configuration for all tests."""
import typing

import pytest

import httpstan.main


@pytest.fixture(scope="module")
def httpstan_server() -> typing.Generator[httpstan.main.Server, None, None]:
    """Return event loop with httpstan server already running.

    HTTP server shutdown is handled as well.
    """
    server = httpstan.main.Server()
    server.start()
    yield server
    server.stop()


@pytest.fixture(scope="module")
def api_url(httpstan_server: httpstan.main.Server) -> str:
    host, port = httpstan_server.host, httpstan_server.port
    return f"http://{host}:{port}/v1"
