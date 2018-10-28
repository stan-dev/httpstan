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

    sample_writer:["lp__","accept_stat__","stepsize__","treedepth__","n_leapfrog__","divergent__","energy__","y"]
    sample_writer:[-3.16745e-06,0.999965,1,2,3,0,0.0142087,0.00251692]

If adaptation happens, however, ``sample_writer`` receives messages similar to
the following after the header but before the draws::

    sample_writer:"Adaptation terminated"
    sample_writer:"Step size = 0.809818"
    sample_writer:"Diagonal elements of inverse mass matrix:"
    sample_writer:0.961989

``message_writer`` receives string messages. Some are useful.

``init_writer`` receives only one value, a valid initial value of the parameters
of the model on the unconstrained scale.

``error_writer`` receives error messages.

"""
import ujson as json
import re
from typing import Optional

import httpstan.callbacks_writer_pb2 as callbacks_writer_pb2

TopicEnum = callbacks_writer_pb2.WriterMessage.Topic


class WriterParser:
    """Parse raw Stan writer output into Protocol Buffer messages.

    This currently something of a state machine since Stan only tells us the names
    of the parameters being sampled before the first sample.

    With luck, the writer callbacks in stan::services will eventually provide
    directly the context which this class recovers. At this point, this class
    may be removed.

    """

    def __init__(self):  # noqa
        self.sample_fields, self.diagnostic_fields = None, None
        self.processing_adaptation = None  # learn from output if adaptation happened
        self.previous_message = None  # used for detecting last adaptation message

    def parse(self, message: str) -> Optional[callbacks_writer_pb2.WriterMessage]:
        """Convert raw writer message into protobuf message.

        This function delegates further parsing to message-specific parser.

        """
        writer_name, body = (val.strip() for val in message.split(":", 1))
        if not body:
            return None  # ignore blank lines

        # `body` is either a list or a single value
        try:
            values = json.loads(body)
        except ValueError:
            values = [body]
        if not isinstance(values, list):
            values = [values]

        handler = getattr(self, f"parse_{writer_name}")
        result = handler(values)
        self.previous_message = message
        return result

    def parse_sample_writer(self, values) -> Optional[callbacks_writer_pb2.WriterMessage]:
        """Convert raw writer message into protobuf message."""
        if self.sample_fields is None:
            self.sample_fields = values
            return None

        if self.processing_adaptation is None:
            self.processing_adaptation = bool(re.match(r"^Adaptation terminated", str(values[0])))

        message = callbacks_writer_pb2.WriterMessage(topic=TopicEnum.Value("SAMPLE"))
        if self.processing_adaptation:
            # detect if we are on last adaptation message
            is_last_adaptation_message = re.match(
                r"sample_writer:Diagonal elements of inverse mass matrix:", self.previous_message
            )
            if is_last_adaptation_message:
                self.processing_adaptation = False
            for value in values:
                if isinstance(values[0], str):
                    message.feature.add().string_list.value.append(value)
                else:
                    message.feature.add().double_list.value.append(value)
        else:
            if isinstance(values[0], str):
                # after sampling, we get messages such as "Elapsed Time: ..."
                for value in values:
                    message.feature.add().string_list.value.append(value)
                return message
            # typical case: draws
            for key, value in zip(self.sample_fields, values):
                feature = message.feature.add()
                feature.name = key
                feature.double_list.value.append(value)
        return message

    def parse_diagnostic_writer(self, values):
        """Convert raw writer message into protobuf message."""
        if self.diagnostic_fields is None:
            self.diagnostic_fields = values
            return
        message = callbacks_writer_pb2.WriterMessage(topic=TopicEnum.Value("DIAGNOSTIC"))
        if isinstance(values[0], str):
            # after sampling, we get messages such as "Elapsed Time: ..."
            for value in values:
                message.feature.add().string_list.value.append(value)
            return message
        for key, value in zip(self.diagnostic_fields, values):
            feature = message.feature.add()
            feature.name = key
            feature.double_list.value.append(value)
        return message

    def parse_logger(self, values) -> callbacks_writer_pb2.WriterMessage:
        """Convert raw writer message into protobuf message."""
        message = callbacks_writer_pb2.WriterMessage(topic=TopicEnum.Value("LOGGER"))
        for value in values:
            message.feature.add().string_list.value.append(value)
        return message

    def parse_init_writer(self, values) -> callbacks_writer_pb2.WriterMessage:
        """Convert raw writer message into protobuf message."""
        message = callbacks_writer_pb2.WriterMessage(topic=TopicEnum.Value("INITIALIZATION"))
        for value in values:
            message.feature.add().double_list.value.append(value)
        return message
