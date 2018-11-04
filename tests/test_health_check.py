"""Test health check route."""
import asyncio

import requests


def test_health_check(api_url):
    """Test health check route."""

    async def main():
        resp = requests.get(f"{api_url}/health")
        assert resp.status_code == 200

    asyncio.get_event_loop().run_until_complete(main())
