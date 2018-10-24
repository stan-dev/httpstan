import marshmallow
import marshmallow.fields as fields
import marshmallow.validate as validate


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
