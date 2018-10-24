"""Helper functions for tests."""
import json
import typing

import aiohttp
import google.protobuf.internal.decoder
import httpstan.callbacks_writer_pb2 as callbacks_writer_pb2


def validate_protobuf_messages(fit_bytes):
    """Superficially validate samples from a Stan model."""
    varint_decoder = google.protobuf.internal.decoder._DecodeVarint32
    next_pos, pos = 0, 0
    while pos < len(fit_bytes):
        msg = callbacks_writer_pb2.WriterMessage()
        next_pos, pos = varint_decoder(fit_bytes, pos)
        msg.ParseFromString(fit_bytes[pos : pos + next_pos])
        assert msg
        pos += next_pos


def extract_draws(fit_bytes, param_name):
    """Extract all draws for parameter from stream response.

    Only works with a single parameter.

    Arguments:
        response (aiohttp.StreamReader): streaming response content
        param_name (str): (flat) parameter name

    Returns:
        list of int or double: draws of `param_name`.

    """
    draws = []

    varint_decoder = google.protobuf.internal.decoder._DecodeVarint32
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
    async with aiohttp.ClientSession() as session:
        models_url = "http://{}:{}/v1/models".format(host, port)
        headers = {"content-type": "application/json"}
        async with session.post(
            models_url, data=json.dumps({"program_code": program_code}), headers=headers
        ) as resp:
            assert resp.status == 201
            model_name = (await resp.json())["name"]

        fits_url = f"http://{host}:{port}/v1/models/{model_name.split('/')[-1]}/fits"
        async with session.post(fits_url, data=json.dumps(fit_payload), headers=headers) as resp:
            assert resp.status == 201, await resp.json()
            name = (await resp.json())["name"]
        async with aiohttp.ClientSession() as session:
            fit_url = f"http://{host}:{port}/v1/{name}"
            async with session.get(fit_url, headers=headers) as resp:
                assert resp.status == 200, await resp.json()
                fit_bytes = await resp.read()
                return extract_draws(fit_bytes, param_name)
