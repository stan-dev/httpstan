"""Test compiling functions."""
import asyncio
import json

import aiohttp

headers = {"content-type": "application/json"}


def test_compile_invalid_distribution(httpstan_server):
    """Check that compiler error is returned to client."""
    host, port = httpstan_server.host, httpstan_server.port

    program_code = "parameters {real z;} model {z ~ no_such_distribution();}"

    async def main():
        models_url = "http://{}:{}/v1/models".format(host, port)
        payload = {"program_code": program_code}
        async with aiohttp.ClientSession() as session:
            async with session.post(models_url, data=json.dumps(payload), headers=headers) as resp:
                assert resp.status == 400
                payload = await resp.json()
                assert "error" in payload and "message" in payload["error"]
                assert (
                    "Probability function must end in _lpdf or _lpmf" in payload["error"]["message"]
                )

    asyncio.get_event_loop().run_until_complete(main())
