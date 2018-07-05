"""Helper functions for tests."""
import json
import typing

import aiohttp

import httpstan.callbacks_writer_pb2


async def extract_draws(response, param_name):
    """Extract all draws for parameter from stream response.

    Only works with a single parameter.

    Arguments:
        response (aiohttp.StreamReader): streaming response content
        param_name (str): (flat) parameter name

    Returns:
        list of int or double: draws of `param_name`.

    """
    draws = []
    assert response.status == 200
    while True:
        chunk = await response.content.readline()
        if not chunk:
            break
        assert len(chunk)
        payload = json.loads(chunk)
        assert len(payload) > 0
        assert "topic" in payload
        assert "LOGGER" in httpstan.callbacks_writer_pb2.WriterMessage.Topic.keys()
        assert "SAMPLE" in httpstan.callbacks_writer_pb2.WriterMessage.Topic.keys()
        if payload["topic"] == "SAMPLE":
            assert isinstance(payload["feature"], dict)
            if param_name in payload["feature"]:
                value_wrapped = payload["feature"][param_name]
                kind = "doubleList" if "doubleList" in value_wrapped else "intList"
                draws.append(value_wrapped[kind]["value"].pop())
    if len(draws) == 0:
        raise KeyError(f"No draws found for parameter `{param_name}`.")
    return draws


async def sample_then_extract(
    host: str, port: int, program_code: str, actions_payload: dict, param_name: str
) -> typing.List[typing.Union[int, float]]:
    """Combines common steps in tests.

    Arguments:
        host: host
        port: port
        program_code: Stan program code
        actions_payload: Python dict, to be converted into JSON and passed to /actions
        param_name : (flat) parameter name

    Returns:
        Draws of `param_name`.

    """
    async with aiohttp.ClientSession() as session:
        models_url = "http://{}:{}/v1/models".format(host, port)
        headers = {"content-type": "application/json"}
        async with session.post(
            models_url, data=json.dumps({"program_code": program_code}), headers=headers
        ) as resp:
            assert resp.status == 200
            model_id = (await resp.json())["id"]

        models_actions_url = "http://{}:{}/v1/models/{}/actions".format(host, port, model_id)
        async with session.post(
            models_actions_url, data=json.dumps(actions_payload), headers=headers
        ) as resp:
            return await extract_draws(resp, param_name)
