"""Helper functions for tests."""
import asyncio
import typing

import aiohttp
import google.protobuf.internal.decoder
import httpstan.callbacks_writer_pb2 as callbacks_writer_pb2


async def get_model_name(api_url: str, program_code: str) -> str:
    """Compile and retrieve model name.

    This function is a coroutine.
    """
    models_url = f"{api_url}/models"
    payload = {"program_code": program_code}
    async with aiohttp.ClientSession() as session:
        async with session.post(models_url, json=payload) as resp:
            assert resp.status == 201
            response_payload = await resp.json()
    model_name = typing.cast(str, response_payload["name"])
    assert "compiler_output" in response_payload
    return model_name


def extract(param_name: str, fit_bytes: bytes) -> typing.List[typing.Union[int, float]]:
    """Extract all draws for parameter from protobuf stream response.

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
        assert msg
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


async def sample(api_url: str, program_code: str, fit_payload: dict) -> dict:
    """Start sampling operation, returning `Operation`.

    This function is a coroutine.

    Arguments:
        api_url: REST API endpoint
        program_code: Stan program code
        fit_payload: Python dict, to be converted into JSON
        param_name : (flat) parameter name

    Returns:
        Draws of `param_name`.

    """
    model_name = await get_model_name(api_url, program_code)
    payload = fit_payload
    fits_url = f"{api_url}/{model_name}/fits"
    async with aiohttp.ClientSession() as session:
        async with session.post(fits_url, json=payload) as resp:
            assert resp.status == 201
            operation = await resp.json()
            operation_name = operation["name"]
            assert operation_name is not None
            assert operation_name.startswith("operations/")

        operation_url = f"{api_url}/{operation_name}"
        # wait until fit is finished
        while True:
            async with session.get(operation_url) as resp:
                operation = await resp.json()
                if operation["done"]:
                    break
                await asyncio.sleep(0.1)

    return typing.cast(dict, operation)


async def sample_then_extract(
    api_url: str, program_code: str, fit_payload: dict, param_name: str
) -> typing.List[typing.Union[int, float]]:
    """Combines common steps in tests.

    This function is a coroutine.

    Arguments:
        api_url: REST API endpoint
        program_code: Stan program code
        fit_payload: Python dict, to be converted into JSON
        param_name : (flat) parameter name

    Returns:
        Draws of `param_name`.

    """
    operation = await sample(api_url, program_code, fit_payload)
    fit_name = operation["result"]["name"]
    async with aiohttp.ClientSession() as session:
        fit_url = f"{api_url}/{fit_name}"
        async with session.get(fit_url) as resp:
            assert resp.status == 200
            assert resp.headers["Content-Type"] == "application/octet-stream"
            fit_bytes = await resp.read()
    return extract(param_name, fit_bytes)
