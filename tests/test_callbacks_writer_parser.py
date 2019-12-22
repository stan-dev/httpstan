"""Test parser for output of stan::services functions."""
import json
import re
from typing import List, Optional

from numpy.testing import assert_almost_equal

import httpstan.callbacks_writer_parser
import httpstan.callbacks_writer_pb2 as callbacks_writer_pb2

TopicEnum = callbacks_writer_pb2.WriterMessage.Topic


def test_callbacks_writer_parser_message_writer() -> None:
    """Test that callback writer messages are parsed correctly."""
    message = b"""logger:Gradient evaluation took 4.7e-05 seconds"""
    message_pb = callbacks_writer_pb2.WriterMessage(topic=TopicEnum.Value("LOGGER"))
    message_pb.feature.add().string_list.value.append(message.split(b":", 1).pop())
    parser = httpstan.callbacks_writer_parser.WriterParser()
    observed = parser.parse(message)
    assert observed == message_pb
