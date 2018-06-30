"""pytest configuration for all tests."""
import pytest

import httpstan.main


@pytest.fixture(scope="module")
def httpstan_server(request):
    """Return event loop with httpstan server already running.

    HTTP server shutdown is handled as well.
    """
    server = httpstan.main.Server()
    server.start()
    yield server
    server.stop()
