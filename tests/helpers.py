"""Helper functions for tests."""
import json

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
        assert 'topic' in payload
        assert 'LOGGER' in httpstan.callbacks_writer_pb2.WriterMessage.Topic.keys()
        assert 'SAMPLE' in httpstan.callbacks_writer_pb2.WriterMessage.Topic.keys()
        if payload['topic'] == 'SAMPLE':
            assert isinstance(payload['feature'], dict)
            if param_name in payload['feature']:
                value_wrapped = payload['feature'][param_name]
                kind = 'doubleList' if 'doubleList' in value_wrapped else 'intList'
                draws.append(value_wrapped[kind]['value'].pop())
    if len(draws) == 0:
        raise KeyError(f'No draws found for parameter `{param_name}`.')
    return draws
