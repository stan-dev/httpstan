"""Test OpenAPI spec generation."""
import httpstan.routes


def test_openapi_spec() -> None:
    """Test OpenAPI spec generation."""
    spec = httpstan.routes.openapi_spec()
    assert spec
    models_endpoint = spec.to_dict()["paths"]["/v1/models"]
    expected = {"$ref": "#/definitions/CreateModelRequest"}
    assert models_endpoint["post"]["parameters"][0]["schema"] == expected
