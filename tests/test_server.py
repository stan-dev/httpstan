"""Rudimentary test of server."""
import aiohttp


def test_server(loop_with_server, host, port):
    """Rudimentary test of server."""
    url = "http://{}:{}/v1/models".format(host, port)

    async def main():
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                assert resp.status != 200

    loop_with_server.run_until_complete(main())
