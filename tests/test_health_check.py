"""Test services function argument lookups."""
import aiohttp


def test_health_check(loop_with_server, host, port):
    """Test health check route."""

    async def main():
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://{host}:{port}/v1/health") as resp:
                assert resp.status == 200

    loop_with_server.run_until_complete(main())
