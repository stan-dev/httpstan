"""Rudimentary test of server."""
import asyncio
import aiohttp


def test_server(httpstan_server):
    """Rudimentary test of server."""
    host, port = httpstan_server.host, httpstan_server.port
    url = "http://{}:{}/v1/models".format(host, port)

    async def main():
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                assert resp.status != 200

    asyncio.get_event_loop().run_until_complete(main())
