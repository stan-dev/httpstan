"""Helper functions for tests."""
import asyncio
import typing

import google.protobuf.internal.decoder
import httpstan.callbacks_writer_pb2 as callbacks_writer_pb2
import requests


def get_model_name(api_url: str, program_code: str) -> str:
    """Compile and retrieve model name."""
    resp = requests.post(f"{api_url}/models", json={"program_code": program_code})
    assert resp.status_code == 201, (api_url, resp.content)
    model_name = resp.json()["name"]
    assert "compiler_output" in resp.json()
    return model_name


def validate_protobuf_messages(fit_bytes: bytes) -> None:
    """Superficially validate samples from a Stan model."""
    varint_decoder = google.protobuf.internal.decoder._DecodeVarint32  # type: ignore
    next_pos, pos = 0, 0
    while pos < len(fit_bytes):
        msg = callbacks_writer_pb2.WriterMessage()
        next_pos, pos = varint_decoder(fit_bytes, pos)
        msg.ParseFromString(fit_bytes[pos : pos + next_pos])
        assert msg
        pos += next_pos


def extract_draws(fit_bytes: bytes, param_name: str) -> typing.List[typing.Union[int, float]]:
    """Extract all draws for parameter from stream response.

    Only works with a single parameter.

    Arguments:
        response (aiohttp.StreamReader): streaming response content
        param_name (str): (flat) parameter name

    Returns:
        list of int or double: draws of `param_name`.

    """
    draws = []

    varint_decoder = google.protobuf.internal.decoder._DecodeVarint32  # type: ignore
    next_pos, pos = 0, 0
    while pos < len(fit_bytes):
        msg = callbacks_writer_pb2.WriterMessage()
        next_pos, pos = varint_decoder(fit_bytes, pos)
        msg.ParseFromString(fit_bytes[pos : pos + next_pos])
        pos += next_pos
        if msg.topic == callbacks_writer_pb2.WriterMessage.Topic.Value("SAMPLE"):
            for value_wrapped in msg.feature:
                if param_name == value_wrapped.name:
                    fea = getattr(value_wrapped, "double_list") or getattr(
                        value_wrapped, "int_list"
                    )
                    draws.append(fea.value.pop())
    if len(draws) == 0:
        raise KeyError(f"No draws found for parameter `{param_name}`.")
    return draws


async def sample_then_extract(
    host: str, port: int, program_code: str, fit_payload: dict, param_name: str
) -> typing.List[typing.Union[int, float]]:
    """Combines common steps in tests.

    Arguments:
        host: host
        port: port
        program_code: Stan program code
        fit_payload: Python dict, to be converted into JSON
        param_name : (flat) parameter name

    Returns:
        Draws of `param_name`.

    """
    api_url = f"http://{host}:{port}/v1"
    resp = requests.post(f"{api_url}/models", json={"program_code": program_code})
    assert resp.status_code == 201
    model_name = resp.json()["name"]
    del resp

    resp = requests.post(f"{api_url}/{model_name}/fits", json=fit_payload)
    assert resp.status_code == 201
    operation = resp.json()
    operation_name = operation["name"]
    assert operation_name is not None
    assert operation_name.startswith("operations/"), (f"{api_url}/{model_name}/fits", operation)

    fit_name = operation["metadata"]["fit"]["name"]

    resp = requests.get(f"{api_url}/{operation_name}")
    assert resp.status_code == 200

    # wait until fit is finished
    while not requests.get(f"{api_url}/{operation_name}").json()["done"]:
        await asyncio.sleep(0.1)

    resp = requests.get(f"{api_url}/{fit_name}")
    assert resp.status_code == 200, resp.json()
    fit_bytes = resp.content
    return extract_draws(fit_bytes, param_name)
