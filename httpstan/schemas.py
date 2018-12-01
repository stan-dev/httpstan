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
    def validate_result(self, data):
        if data["done"] and data.get("result") is None:
            raise marshmallow.ValidationError("If `done` then `result` must be set.", "result")
        if not data["done"] and data.get("result"):
            raise marshmallow.ValidationError(
                "If not `done` then `result` must be empty.", "result"
            )


class Status(marshmallow.Schema):
    """Error."""

    code = fields.Integer(required=True)
    status = fields.String(required=True)
    message = fields.String(required=True)
    details = fields.List(fields.Dict())


class CreateModelRequest(marshmallow.Schema):
    program_code = fields.String(required=True)


class Model(marshmallow.Schema):
    name = fields.String(required=True)
    compiler_output = fields.String(required=True)


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
