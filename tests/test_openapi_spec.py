"""Test OpenAPI spec generation."""
import httpstan.openapi


def test_openapi_spec() -> None:
    """Test OpenAPI spec generation."""
    spec = httpstan.openapi.openapi_spec()
    assert spec
    models_endpoint = spec.to_dict()["paths"]["/v1/models"]
    expected = {"$ref": "#/definitions/CreateModelRequest"}
    assert models_endpoint["post"]["parameters"][0]["schema"] == expected
