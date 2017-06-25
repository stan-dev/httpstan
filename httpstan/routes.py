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
    app.router.add_post('/v1/programs', views.handle_programs)
    app.router.add_post('/v1/programs/{program_id}/actions', views.handle_programs_actions)


def openapi_spec() -> str:
    """Return OpenAPI (fka Swagger) spec for API."""
    spec = apispec.APISpec(
        title='httpstan API',
        version=httpstan.__version__,
        plugins=['apispec.ext.marshmallow'],
    )
    spec.add_path(path='/v1/programs', view=views.handle_programs)
    spec.add_path(path='/v1/programs/{program_id}/actions', view=views.handle_programs_actions)
    spec.definition('Program', schema=views.ProgramSchema)
    spec.definition('ProgramAction', schema=views.ProgramActionSchema)
    return json.dumps(spec.to_dict())
