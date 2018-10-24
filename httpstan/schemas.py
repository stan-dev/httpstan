import marshmallow
import marshmallow.fields as fields
import marshmallow.validate as validate


class Status(marshmallow.Schema):
    """Part of Error schema."""

    code = fields.Integer(required=True)
    status = fields.String(required=True)
    message = fields.String(required=True)
    details = fields.List(fields.Dict())


class Error(marshmallow.Schema):
    """Error schema.

    Follows Google's API Design.
    """

    error = fields.Nested(Status, required=True)


class CreateModelRequest(marshmallow.Schema):
    program_code = fields.String(required=True)


class Model(marshmallow.Schema):
    name = fields.String(required=True)


# TODO(AR): supported functions can be fetched from stub Python files
SERVICES_FUNCTION_NAMES = frozenset(
    {"stan::services::sample::hmc_nuts_diag_e", "stan::services::sample::hmc_nuts_diag_e_adapt"}
)


class CreateFitRequest(marshmallow.Schema):
    function = fields.String(required=True, validate=validate.OneOf(SERVICES_FUNCTION_NAMES))
    data = fields.Dict(missing={})


class Fit(marshmallow.Schema):
    # e.g., models/15d69926a05591e1/fits/66ff16fc9d25cd29
    name = fields.String(required=True)


class ShowParamsRequest(marshmallow.Schema):
    data = fields.Dict(required=True)


class Parameter(marshmallow.Schema):  # noqa
    """Schema for single parameter."""

    name = fields.String(required=True)
    dims = fields.List(fields.Integer(), required=True)
    constrained_names = fields.List(fields.String(), required=True)
