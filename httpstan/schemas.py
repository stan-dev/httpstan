import numbers
import typing

import marshmallow
import marshmallow.fields as fields
import marshmallow.validate as validate


class Operation(marshmallow.Schema):
    """Long-running operation.

    Modeled on `operations.proto`, linked in
    https://cloud.google.com/apis/design/standard_methods

    """

    name = fields.String(required=True)
    metadata = fields.Dict()
    done = fields.Bool(required=True)
    # if `done` is False, `result` is empty, otherwise an `error` or valid `response`.
    result = fields.Dict()

    @marshmallow.validates_schema
    def validate_result(self, data: dict, many: bool, partial: bool) -> None:
        assert not many and not partial, "Use of `many` and `partial` with schema unsupported."
        if data["done"] and data.get("result") is None:  # pragma: no cover
            raise marshmallow.ValidationError("If `done` then `result` must be set.", "result")
        if not data["done"] and data.get("result"):  # pragma: no cover
            raise marshmallow.ValidationError("If not `done` then `result` must be empty.", "result")


class Status(marshmallow.Schema):
    """Error.

    Modeled on ``google.rpc.Status``. See
    https://cloud.google.com/apis/design/errors

    """

    code = fields.Integer(required=True)
    status = fields.String(required=True)
    message = fields.String(required=True)
    details = fields.List(fields.Dict())


class CreateModelRequest(marshmallow.Schema):
    """Schema for request to build a Stan program."""

    program_code = fields.String(required=True)


class Model(marshmallow.Schema):
    name = fields.String(required=True)
    compiler_output = fields.String(required=True)
    stanc_warnings = fields.String(required=True)


class Data(marshmallow.Schema):
    """Data for a Stan model."""

    class Meta:
        unknown = marshmallow.INCLUDE

    @marshmallow.validates_schema
    def validate_stan_values(self, data: dict, many: bool, partial: bool) -> None:
        """Verify ``data`` dictionary will work for Stan.

        Keys should be strings, values must be numbers or (nested) lists of numbers.

        """
        assert not many and not partial, "Use of `many` and `partial` with schema unsupported."

        def is_nested_list_of_numbers(value: typing.Any) -> bool:
            if not isinstance(value, list):
                return False
            return all(isinstance(val, numbers.Number) or is_nested_list_of_numbers(val) for val in value)

        for key, value in data.items():
            if isinstance(value, numbers.Number):
                continue  # scalar value
            elif not is_nested_list_of_numbers(value):
                raise marshmallow.ValidationError(
                    f"Values associated with `{key}` must be (nested) sequences of numbers."
                )


class CreateFitRequest(marshmallow.Schema):
    """Schema for request to start sampling.

    Only two algorithms are supported: ``hmc_nuts_diag_e_adapt`` and ``fixed_param``.

    Sampler parameters can be found in ``httpstan/stan_services.cpp``.

    """

    function = fields.String(
        required=True,
        validate=validate.OneOf(
            ["stan::services::sample::hmc_nuts_diag_e_adapt", "stan::services::sample::fixed_param"]
        ),
    )
    data = fields.Nested(Data(), missing={})
    init = fields.Nested(Data(), missing={})
    random_seed = fields.Integer(validate=validate.Range(min=0))
    chain = fields.Integer(validate=validate.Range(min=0))
    init_radius = fields.Number()
    num_warmup = fields.Integer(validate=validate.Range(min=0))
    num_samples = fields.Integer(validate=validate.Range(min=0))
    num_thin = fields.Integer(validate=validate.Range(min=0))
    save_warmup = fields.Boolean()
    refresh = fields.Integer(validate=validate.Range(min=0))
    stepsize = fields.Number()
    stepsize_jitter = fields.Number()
    max_depth = fields.Integer(validate=validate.Range(min=0))
    delta = fields.Number()
    gamma = fields.Number()
    kappa = fields.Number()
    t0 = fields.Number()
    init_buffer = fields.Integer(validate=validate.Range(min=0))
    term_buffer = fields.Integer(validate=validate.Range(min=0))
    window = fields.Integer(validate=validate.Range(min=0))


class Fit(marshmallow.Schema):
    # e.g., models/15d69926a05591e1/fits/66ff16fc9d25cd29
    name = fields.String(required=True)


class ShowParamsRequest(marshmallow.Schema):
    data = fields.Nested(Data(), missing={})


class Parameter(marshmallow.Schema):  # noqa
    """Schema for single parameter."""

    name = fields.String(required=True)
    dims = fields.List(fields.Integer(), required=True)
    constrained_names = fields.List(fields.String(), required=True)


class WriterMessage(marshmallow.Schema):
    """Messages from callback writers and loggers in ``stan::callbacks``.

    NOTE: You SHOULD NOT use this schema. This schema exists for testing and
    for documentation. It SHOULD NOT be used to process a large number of JSON
    messages. Doing so will slow down any program.

    This schema is intended for messages emitted by C++ classes which inherit
    from

    - ``stan/callbacks/writer.hpp``, and
    - ``stan/callbacks/logger.hpp``.

    In particular, the schema matches a JSON-based "version" of the CSV-focused
    ``stan/callbacks/stream_writer.hpp`` and
    ``stan/callbacks/stream_logger.hpp``.

    This version is found "inside" the httpstan-specific
    ``httpstan/socket_writer.hpp`` and ``httpstan/socket_logger.hpp``.

    `WriterMessage` is a data format for all messages written by the callback
    writers defined in ``stan::callbacks``.  These writers are used by the
    functions defined in ``stan::services``. For example,
    ``stan::services::sample::hmc_nuts_diag_e`` uses one logger and three
    writers:

    - ``logger`` Logger for informational and error messages
    - ``init_writer`` Writer callback for unconstrained inits
    - ``sample_writer`` Writer for draws
    - ``diagnostic_writer`` Writer for diagnostic information

    WriterMessage is a format which is flexible enough to accommodate these
    different uses while still providing a predictable structure.

    A WriterMessage has a field ``topic`` which provides information about what
    the WriterMessage concerns or what produced it. For example, the `topic`
    associated with a WriterMessage written by `sample_writer` in the function
    is ``sample``.

    The "content" of a message is stored in the field ``values``. This is either
    a list or a mapping.

    """

    version = fields.Integer(required=True)
    topic = fields.String(required=True, validate=validate.OneOf(["logger", "initialization", "sample", "diagnostic"]))
    # values is either a List or a Mapping. Marshmallow lacks a union type.
    values = fields.Raw(required=True)


class ShowLogProbRequest(marshmallow.Schema):
    """Schema for log_prob request."""

    data = fields.Nested(Data(), missing={})
    unconstrained_parameters = fields.List(fields.Float(), required=True)
    adjust_transform = fields.Boolean(missing=True)


class ShowLogProbGradRequest(marshmallow.Schema):
    """Schema for log_prob_grad request."""

    data = fields.Nested(Data(), missing={})
    unconstrained_parameters = fields.List(fields.Float(), required=True)
    adjust_transform = fields.Boolean(missing=True)


class ShowWriteArrayRequest(marshmallow.Schema):
    """Schema for write_array request."""

    data = fields.Nested(Data(), missing={})
    unconstrained_parameters = fields.List(fields.Float(), required=True)
    include_tparams = fields.Boolean(missing=True)
    include_gqs = fields.Boolean(missing=True)


class ShowTransformInitsRequest(marshmallow.Schema):
    """Schema for transform_inits request."""

    data = fields.Nested(Data(), missing={})
    constrained_parameters = fields.Nested(Data(), required=True)
