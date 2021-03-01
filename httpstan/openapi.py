"""Define OpenAPI spec for HTTP-based REST API.

Only used for building documentation. Users should never import this file. If
they do they will likely encounter an ``ImportError`` due to the fact that they
have not installed ``apispec``.

"""
from typing import Callable

import apispec
import apispec.ext.marshmallow
import apispec.utils
import apispec.yaml_utils

import httpstan
import httpstan.views as views

try:
    version = httpstan.__version__
except AttributeError:
    from doc.conf import version  # type: ignore


class DocPlugin(apispec.BasePlugin):
    def init_spec(self, spec: apispec.APISpec) -> None:
        super().init_spec(spec)

    def operation_helper(self, operations: dict, view: Callable, **kwargs: dict) -> None:
        """Operation helper that parses docstrings for operations. Adds a
        ``func`` parameter to `apispec.APISpec.path`.
        """
        doc_operations = apispec.yaml_utils.load_operations_from_docstring(view.__doc__)
        operations.update(doc_operations)


def openapi_spec() -> apispec.APISpec:
    """Return OpenAPI (fka Swagger) spec for API."""
    spec = apispec.APISpec(
        title="httpstan HTTP-based REST API",
        version=version,
        openapi_version="2.0",
        # plugin order, MarshmallowPlugin resolves schema references created by DocPlugin
        plugins=[DocPlugin(), apispec.ext.marshmallow.MarshmallowPlugin()],
    )
    spec.path(path="/v1/health", view=views.handle_health)
    spec.path(path="/v1/models", view=views.handle_create_model)
    spec.path(path="/v1/models", view=views.handle_list_models)
    spec.path(path="/v1/models/{model_id}", view=views.handle_delete_model)
    spec.path(path="/v1/models/{model_id}/params", view=views.handle_show_params)
    spec.path(path="/v1/models/{model_id}/log_prob", view=views.handle_log_prob)
    spec.path(path="/v1/models/{model_id}/log_prob_grad", view=views.handle_log_prob_grad)
    spec.path(path="/v1/models/{model_id}/write_array", view=views.handle_write_array)
    spec.path(path="/v1/models/{model_id}/transform_inits", view=views.handle_transform_inits)
    spec.path(path="/v1/models/{model_id}/fits", view=views.handle_create_fit)
    spec.path(path="/v1/models/{model_id}/fits/{fit_id}", view=views.handle_get_fit)
    spec.path(path="/v1/models/{model_id}/fits/{fit_id}", view=views.handle_delete_fit)
    spec.path(path="/v1/operations/{operation_id}", view=views.handle_get_operation)
    apispec.utils.validate_spec(spec)
    return spec
