"""Routes for httpstan.

Routes for the HTTP server are defined here.
"""
from typing import Callable

import apispec
import apispec.ext.marshmallow
import apispec.utils
import apispec.yaml_utils
import aiohttp.web

import httpstan
import httpstan.views as views


def setup_routes(app: aiohttp.web.Application) -> None:
    """Add routes to Application.

    Arguments:
        app (aiohttp.Application): Application to which routes should be added.

    """
    app.router.add_get("/v1/health", views.handle_health)
    app.router.add_post("/v1/models", views.handle_models)
    app.router.add_post("/v1/models/{model_id}/params", views.handle_show_params)
    app.router.add_post("/v1/models/{model_id}/fits", views.handle_create_fit)
    app.router.add_get("/v1/models/{model_id}/fits/{fit_id}", views.handle_get_fit)
    app.router.add_get("/v1/operations/{operation_id}", views.handle_get_operation)


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
        version=httpstan.__version__,
        openapi_version="2.0",
        # plugin order, MarshmallowPlugin resolves schema references created by DocPlugin
        plugins=[DocPlugin(), apispec.ext.marshmallow.MarshmallowPlugin()],
    )
    spec.path(path="/v1/health", view=views.handle_health)
    spec.path(path="/v1/models", view=views.handle_models)
    spec.path(path="/v1/models/{model_id}/params", view=views.handle_show_params)
    spec.path(path="/v1/models/{model_id}/fits", view=views.handle_create_fit)
    spec.path(path="/v1/models/{model_id}/fits/{fit_id}", view=views.handle_get_fit)
    spec.path(path="/v1/operations/{operation_id}", view=views.handle_get_operation)
    apispec.utils.validate_spec(spec)
    return spec
