"""Test health check route."""
import aiohttp
import pytest


@pytest.mark.asyncio
async def test_health_check(api_url: str) -> None:
    """Test health check route."""

    health_check_url = f"{api_url}/health"
    async with aiohttp.ClientSession() as session:
        async with session.get(health_check_url) as resp:
            assert resp.status == 200
