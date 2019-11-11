"""Routes for httpstan.

Routes for the HTTP server are defined here.
"""
import aiohttp.web

import httpstan.views as views


def setup_routes(app: aiohttp.web.Application) -> None:
    """Add routes to Application.

    Arguments:
        app (aiohttp.Application): Application to which routes should be added.

    """
    # Note: changes here must be mirrored in `openapi.py`.
    app.router.add_get("/v1/health", views.handle_health)
    app.router.add_post("/v1/models", views.handle_models)
    app.router.add_post("/v1/models/{model_id}/params", views.handle_show_params)
    app.router.add_post("/v1/models/{model_id}/fits", views.handle_create_fit)
    app.router.add_get("/v1/models/{model_id}/fits/{fit_id}", views.handle_get_fit)
    app.router.add_get("/v1/operations/{operation_id}", views.handle_get_operation)
