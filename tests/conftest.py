"""pytest configuration for all tests."""
import asyncio
import pytest

import httpstan.main


@pytest.fixture(scope='session')
def host():
    """Host for server to listen on."""
    return '127.0.0.1'


@pytest.fixture(scope='session')
def port():
    """Port for server to listen on."""
    return 8080


@pytest.fixture(scope='module')
def loop_with_server(request, host, port):
    """Return event loop with httpstan server already running.

    HTTP server shutdown is handled as well.
    """
    l = asyncio.new_event_loop()
    asyncio.set_event_loop(None)

    # setup server
    app = httpstan.main.make_app(l)
    handler = app.make_handler(loop=l)
    srv = l.run_until_complete(l.create_server(handler, host, port))
    l.run_until_complete(app.startup())

    yield l  # yield control, test proper would start here

    # shutdown server
    srv.close()
    l.run_until_complete(srv.wait_closed())
    l.run_until_complete(app.shutdown())
    l.run_until_complete(handler.shutdown(60.0))
    l.run_until_complete(app.cleanup())

    # close loop
    l.close()
