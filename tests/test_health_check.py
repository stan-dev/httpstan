"""Test health check route."""
import asyncio
import aiohttp


def test_health_check(httpstan_server):
    """Test health check route."""

    host, port = httpstan_server.host, httpstan_server.port

    async def main():
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://{host}:{port}/v1/health") as resp:
                assert resp.status == 200

    asyncio.get_event_loop().run_until_complete(main())
