"""Test OpenAPI spec generation."""
import httpstan.routes


def test_openapi_spec() -> None:
    """Test OpenAPI spec generation."""
    spec = httpstan.routes.openapi_spec()
    assert spec
    assert isinstance(spec, str)
