"""Parser for the output of callback writers used by stan::services functions.

For example, stan::services::sample::hmc_nuts_diag_e_adapt writes messages
to the following five writers:

- ``message_writer`` Writer for messages
- ``error_writer`` Writer for messages
- ``init_writer`` Writer callback for unconstrained inits
- ``sample_writer`` Writer for draws
- ``diagnostic_writer`` Writer for diagnostic information

``sample_writer`` and ``diagnostic_writer`` receive messages in a predictable
fashion: headers followed by samples. For example::

    sample_writer:{{ protobuf version of ["lp__","accept_stat__","stepsize__","treedepth__","n_leapfrog__","divergent__","energy__","y"] }}
    sample_writer:{{ protobuf version of [-3.16745e-06,0.999965,1,2,3,0,0.0142087,0.00251692] }}

If adaptation happens, however, ``sample_writer`` receives messages similar to
the following after the header but before the draws::

    sample_writer:{{ protobuf version of "Adaptation terminated" }}
    sample_writer:{{ protobuf version of "Step size = 0.809818" }}
    sample_writer:{{ protobuf version of "Diagonal elements of inverse mass matrix:" }}
    sample_writer:{{ protobuf version of "0.961989" }}

``message_writer`` receives string messages. Some are useful.

``init_writer`` receives only one value, a valid initial value of the parameters
of the model on the unconstrained scale.

``error_writer`` receives error messages.

"""
import re
import typing

import google.protobuf.internal.decoder as decoder
import google.protobuf.message
import google.protobuf.wrappers_pb2 as wrappers_pb2

import httpstan.callbacks_writer_pb2 as callbacks_writer_pb2

TopicEnum = callbacks_writer_pb2.WriterMessage.Topic
DoubleList = callbacks_writer_pb2.WriterMessage.DoubleList
StringList = callbacks_writer_pb2.WriterMessage.StringList

def _parse_delimited_message(buffer: bytes) -> typing.Tuple[bytes, int]:
    """Parse a length-delimited Protobuf message.

    Arguments:
        buffer: One or more length-delimited protobuf string

    Returns:
        Message bytes and count of bytes of `buffer` read.
    """
    msg_len, new_pos = decoder._DecodeVarint32(buffer, 0)
    msg_buf = buffer[new_pos:new_pos+msg_len]
    return msg_buf, new_pos + msg_len


class WriterParser:
    """Parse Stan writer and logger Protobuf-encoded output.

    This currently is something of a state machine since Stan only tells us the names
    of the parameters being sampled before the first sample.

    With luck, the writer callbacks in stan::services will eventually provide
    directly the context which this class recovers.

    """

    def __init__(self) -> None:
        self.sample_fields: typing.Optional[list] = None
        self.diagnostic_fields: typing.Optional[list] = None
        self.processing_adaptation: typing.Optional[
            bool
        ] = None  # learn from output if adaptation happened
        self.previous_message: typing.Optional[
            str
        ] = None  # used for detecting last adaptation message

    def parse(self, message: bytes) -> typing.Optional[callbacks_writer_pb2.WriterMessage]:
        """Convert raw message sequence into a WriterMessage.

        This function delegates further parsing to message-specific parser.

        """
        writer_name, body = (val for val in message.split(b":", 1))
        if not body.strip():
            return None  # ignore blank lines

        # bizarre edge case, skip a particular message
        # not only does the following not raise an error, it parses several values
        # msg_buf = b'\n( Elapsed Time: 0.03331 seconds (Warm-up)'
        # dl = callbacks_writer_pb2.WriterMessage.DoubleList().MergeFromString(msg_buf)
        if b"Elapsed Time:" in body:
            return None

        handler = getattr(self, f"parse_{writer_name.decode()}")
        if b"logger" in writer_name:
            # logger values are just strings (Python bytes), not protobuf-encoded
            return handler([body.decode()])

        # writer messages are either a list of strings or a list of doubles

        # the following `try` block detects what kinds of values are in the
        # sequence (either strings or doubles). Using `MergeFrom` seems to be
        # the only way to reliably generate a `DecodeError`.
        # `DoubleValue.FromString` does not generate an error with version 3.10.0.
        try:
            msg_buf, bytes_read = _parse_delimited_message(body)
            callbacks_writer_pb2.WriterMessage.DoubleList().MergeFromString(msg_buf)
        except google.protobuf.message.DecodeError:
            list_value = callbacks_writer_pb2.WriterMessage.StringList()
            start_pos = 0
            while start_pos < len(body):
                msg_buf, bytes_read = _parse_delimited_message(body[start_pos:])
                list_value.value.append(wrappers_pb2.StringValue.FromString(msg_buf).value)
                start_pos += bytes_read
        else:
            list_value = callbacks_writer_pb2.WriterMessage.DoubleList()
            start_pos = 0
            while start_pos < len(body):
                msg_buf, bytes_read = _parse_delimited_message(body[start_pos:])
                list_value.value.append(wrappers_pb2.DoubleValue.FromString(msg_buf).value)
                start_pos += bytes_read

        result = handler(list_value)
        self.previous_message = message
        # in order to satisfy type checker we must return a known type:
        # either None or WriterMessage.
        # See https://github.com/python/mypy/issues/1693 for discussion
        if result is None:
            return result
        return typing.cast(callbacks_writer_pb2.WriterMessage, result)

    def parse_sample_writer(self, list_value: typing.Union[DoubleList, StringList]) -> typing.Optional[callbacks_writer_pb2.WriterMessage]:
        """Put a DoubleList or StringList into a WriterMessage."""
        if self.sample_fields is None:
            assert list_value.value and isinstance(list_value.value[0], str)
            self.sample_fields = list(list_value.value)
            return None

        if self.processing_adaptation is None:
            self.processing_adaptation = bool(re.match(r"^Adaptation terminated", str(list_value.value[0])))

        message = callbacks_writer_pb2.WriterMessage(topic=TopicEnum.Value("SAMPLE"))
        if self.processing_adaptation:
            # detect if we are on last adaptation message
            self.previous_message = typing.cast(bytes, self.previous_message)
            is_last_adaptation_message = b"Diagonal elements of inverse mass matrix:" in self.previous_message
            if is_last_adaptation_message:
                self.processing_adaptation = False
            if isinstance(list_value.value[0], str):
                message.feature.add().string_list.MergeFrom(list_value)
            else:
                message.feature.add().double_list.MergeFrom(list_value)
        else:
            if isinstance(list_value.value[0], str):
                # after sampling, we get messages such as "Elapsed Time: ..."
                message.feature.add().string_list.MergeFrom(list_value)
                return message
            # typical case: draws
            # debugging tip, `assert len(self.sample_fields) == len(list_value.value)`
            for key, value in zip(self.sample_fields, list_value.value):
                feature = message.feature.add()
                feature.name = key
                feature.double_list.value.append(value)
        return message

    def parse_diagnostic_writer(
        self, list_value: typing.Union[DoubleList, StringList]
    ) -> typing.Optional[callbacks_writer_pb2.WriterMessage]:
        """Put a DoubleList or StringList into a WriterMessage."""
        if self.diagnostic_fields is None:
            assert list_value.value and isinstance(list_value.value[0], str)
            self.diagnostic_fields = list(list_value.value)
            return None
        message = callbacks_writer_pb2.WriterMessage(topic=TopicEnum.Value("DIAGNOSTIC"))
        if isinstance(list_value.value[0], str):
            # after sampling, we get messages such as "Elapsed Time: ..."
            message.feature.add().string_list.MergeFrom(list_value)
            return message
        for key, value in zip(self.diagnostic_fields, list_value.value):
            feature = message.feature.add()
            feature.name = key
            feature.double_list.value.append(value)
        return message

    def parse_logger(self, values: typing.List[str]) -> callbacks_writer_pb2.WriterMessage:
        """Put list of values into a WriterMessage."""
        message = callbacks_writer_pb2.WriterMessage(topic=TopicEnum.Value("LOGGER"))
        for value in values:
            message.feature.add().string_list.value.append(value)
        return message

    def parse_init_writer(self, list_value: typing.Union[DoubleList, StringList]) -> callbacks_writer_pb2.WriterMessage:
        """Put a DoubleList or StringList into a WriterMessage."""
        assert list_value.value and isinstance(list_value.value[0], float)
        message = callbacks_writer_pb2.WriterMessage(topic=TopicEnum.Value("INITIALIZATION"))
        message.feature.add().double_list.MergeFrom(list_value)
        return message
