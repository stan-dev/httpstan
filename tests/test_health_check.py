"""Test health check route."""
import asyncio

import requests


def test_health_check(httpstan_server):
    """Test health check route."""

    host, port = httpstan_server.host, httpstan_server.port

    async def main():
        resp = requests.get(f"http://{host}:{port}/v1/health")
        assert resp.status_code == 200

    asyncio.get_event_loop().run_until_complete(main())
