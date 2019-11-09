"""Test compiling functions."""
import asyncio

import requests


def test_compile_invalid_distribution(api_url: str) -> None:
    """Check that compiler error is returned to client."""

    program_code = "parameters {real z;} model {z ~ no_such_distribution();}"

    async def main() -> None:
        resp = requests.post(f"{api_url}/models", json={"program_code": program_code})
        assert resp.status_code == 400
        resp_dict = resp.json()
        assert "message" in resp_dict
        assert "Probability function must end in _lpdf" in resp_dict["message"]

    asyncio.get_event_loop().run_until_complete(main())


def test_compile_unknown_arg(api_url: str) -> None:
    """Check that compiler error is returned to client.

    This error can be detected by schema validation.

    """

    program_code = "parameters {real z;} model {z ~ no_such_distribution();}"

    async def main() -> None:
        resp = requests.post(
            f"{api_url}/models", json={"unknown_arg": "abc", "program_code": program_code}
        )
        assert resp.status_code == 422
        assert "unknown_arg" in resp.json()

    asyncio.get_event_loop().run_until_complete(main())
