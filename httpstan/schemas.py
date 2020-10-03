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
        if data["done"] and data.get("result") is None:
            raise marshmallow.ValidationError("If `done` then `result` must be set.", "result")
        if not data["done"] and data.get("result"):
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

    Only one algorithm is currently supported: ``hmc_nuts_diag_e_adapt``.

    Sampler parameters can be found in ``httpstan/stan_services.cpp``.

    """

    function = fields.String(required=True, validate=validate.Equal("stan::services::sample::hmc_nuts_diag_e_adapt"))
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
