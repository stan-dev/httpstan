"""Routes for httpstan.

Routes for the HTTP server are defined here.
"""
import json

import apispec

import httpstan
import httpstan.schemas as schemas
import httpstan.views as views


def setup_routes(app):
    """Add routes to Application.

    Arguments:
        app (aiohttp.Application): Application to which routes should be added.

    """
    app.router.add_get("/v1/health", views.handle_health)
    app.router.add_post("/v1/models", views.handle_models)
    app.router.add_post("/v1/models/{model_id}/params", views.handle_models_params)
    app.router.add_post("/v1/models/{model_id}/fits", views.handle_create_fit)
    app.router.add_get("/v1/models/{model_id}/fits/{fit_id}", views.handle_get_fit)


def openapi_spec() -> str:
    """Return OpenAPI (fka Swagger) spec for API."""
    spec = apispec.APISpec(
        title="httpstan API", version=httpstan.__version__, plugins=["apispec.ext.marshmallow"]
    )
    spec.add_path(path="/v1/health", view=views.handle_health)
    spec.add_path(path="/v1/models", view=views.handle_models)
    spec.add_path(path="/v1/models/{model_id}/params", view=views.handle_models_params)
    spec.add_path(path="/v1/models/{model_id}/fits", view=views.handle_create_fit)
    spec.add_path(path="/v1/models/{model_id}/fits/{fit_id}", view=views.handle_get_fit)
    spec.definition("CreateFitRequest", schema=schemas.CreateFitRequest)
    spec.definition("Error", schema=schemas.Error)
    spec.definition("Fit", schema=schemas.Fit)
    spec.definition("Model", schema=schemas.Model)
    spec.definition("Param", schema=views.ParamSchema)
    return json.dumps(spec.to_dict())
