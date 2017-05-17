"""Rudimentary test of server."""
import aiohttp


def test_server(loop_with_server):
    """Rudimentary test of server."""
    host, port = '127.0.0.1', 8080
    url = 'http://{}:{}/v1/programs'.format(host, port)

    async def main(loop):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                assert resp.status != 200

    loop_with_server.run_until_complete(main(loop_with_server))
