"""Routes for httpstan.

Routes for the HTTP server are defined here.
"""
import json

import apispec

import httpstan
import httpstan.views as views


def setup_routes(app):
    """Add routes to Application.

    Arguments:
        app (aiohttp.Application): Application to which routes should be added.

    """
    app.router.add_get("/v1/health", views.handle_health)
    app.router.add_post("/v1/models", views.handle_models)
    app.router.add_post("/v1/models/{model_id}/actions", views.handle_models_actions)
    app.router.add_post("/v1/models/{model_id}/params", views.handle_models_params)


def openapi_spec() -> str:
    """Return OpenAPI (fka Swagger) spec for API."""
    spec = apispec.APISpec(
        title="httpstan API", version=httpstan.__version__, plugins=["apispec.ext.marshmallow"]
    )
    spec.add_path(path="/v1/health", view=views.handle_health)
    spec.add_path(path="/v1/models", view=views.handle_models)
    spec.add_path(path="/v1/models/{model_id}/actions", view=views.handle_models_actions)
    spec.add_path(path="/v1/models/{model_id}/params", view=views.handle_models_params)
    spec.definition("Model", schema=views.ModelSchema)
    spec.definition("Error", schema=views.ErrorSchema)
    spec.definition("ModelsAction", schema=views.ModelsActionSchema)
    spec.definition("Param", schema=views.ParamSchema)
    return json.dumps(spec.to_dict())
