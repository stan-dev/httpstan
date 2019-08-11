"""Test parser for output of stan::services functions."""
import json
import re

from numpy.testing import assert_almost_equal

import httpstan.callbacks_writer_parser
import httpstan.callbacks_writer_pb2 as callbacks_writer_pb2

TopicEnum = callbacks_writer_pb2.WriterMessage.Topic


def test_callbacks_writer_parser_message_writer() -> None:
    """Test that callback writer messages are parsed correctly."""
    message = """logger:Gradient evaluation took 4.7e-05 seconds"""
    message_pb = callbacks_writer_pb2.WriterMessage(topic=TopicEnum.Value("LOGGER"))
    message_pb.feature.add().string_list.value.append(message.split(":", 1).pop())
    parser = httpstan.callbacks_writer_parser.WriterParser()
    observed = parser.parse(message)
    assert observed == message_pb


def test_callbacks_writer_parser_sample_writer_adapt() -> None:
    """Test that callback writer messages are parsed correctly."""
    messages = (
        """sample_writer:["lp__", "accept_stat__"]""",
        """sample_writer:Adaptation terminated""",
        """sample_writer:Step size = 0.809818""",
    )
    parser = httpstan.callbacks_writer_parser.WriterParser()
    observed = [parser.parse(message) for message in messages]
    expected = [None]
    for message in messages[1:]:
        message_pb = callbacks_writer_pb2.WriterMessage(topic=TopicEnum.Value("SAMPLE"))
        message_pb.feature.add().string_list.value.append(message.split(":", 1).pop())
        expected.append(message_pb)
    assert observed == expected


def test_callbacks_writer_parser_sample_writer() -> None:
    """Test that callback writer messages are parsed correctly."""
    messages = [
        """sample_writer:["lp__","accept_stat__","y"]""",  # noqa
        """sample_writer:[-3.16745e-06,0.999965,0.00251692]""",
    ]
    sample_fields = ["lp__", "accept_stat__", "y"]  # noqa
    values = json.loads("""[-3.16745e-06,0.999965,0.00251692]""")

    parser = httpstan.callbacks_writer_parser.WriterParser()
    observed = [parser.parse(message) for message in messages]

    message_pb = callbacks_writer_pb2.WriterMessage(topic=TopicEnum.Value("SAMPLE"))
    for key, value in zip(sample_fields, values):
        feature = message_pb.feature.add()
        feature.name = key
        feature.double_list.value.append(value)
    expected = [None, message_pb]

    # None == None
    assert observed[0] == expected[0]

    # 'callbacks_writer_pb2.WriterMessage'
    assert type(observed[0]) == type(expected[0])  # noqa: disable=E721

    # handle number and structure

    # pattern for a number
    pattern = r"[-+]*\d+[.]*\d*e*[-+]*\d*"
    observed_num = [float(num) for num in re.findall(pattern, str(observed[1]))]
    expected_num = [float(num) for num in re.findall(pattern, str(expected[1]))]

    # Ignore floating point error
    assert_almost_equal(observed_num, expected_num)

    # replace numbers with text 'NUM'
    observed_structure = re.sub(pattern, "NUM", str(observed[1]))
    expected_structure = re.sub(pattern, "NUM", str(expected[1]))

    assert observed_structure == expected_structure
