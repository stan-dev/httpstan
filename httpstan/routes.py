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
    app.router.add_post("/v1/models", views.handle_create_model)
    app.router.add_get("/v1/models", views.handle_list_models)
    app.router.add_delete("/v1/models/{model_id}", views.handle_delete_model)
    app.router.add_post("/v1/models/{model_id}/params", views.handle_show_params)
    app.router.add_post("/v1/models/{model_id}/log_prob", views.handle_log_prob)
    app.router.add_post("/v1/models/{model_id}/log_prob_grad", views.handle_log_prob_grad)
    app.router.add_post("/v1/models/{model_id}/write_array", views.handle_write_array)
    app.router.add_post("/v1/models/{model_id}/transform_inits", views.handle_transform_inits)
    app.router.add_post("/v1/models/{model_id}/fits", views.handle_create_fit)
    app.router.add_get("/v1/models/{model_id}/fits/{fit_id}", views.handle_get_fit)
    app.router.add_delete("/v1/models/{model_id}/fits/{fit_id}", views.handle_delete_fit)
    app.router.add_get("/v1/operations/{operation_id}", views.handle_get_operation)
