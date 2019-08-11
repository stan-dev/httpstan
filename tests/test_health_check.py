"""Test health check route."""
import asyncio

import requests


def test_health_check(api_url: str) -> None:
    """Test health check route."""

    async def main() -> None:
        resp = requests.get(f"{api_url}/health")
        assert resp.status_code == 200

    asyncio.get_event_loop().run_until_complete(main())
