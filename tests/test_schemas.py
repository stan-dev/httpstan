"""Test Schema validation."""
import pytest
from marshmallow.exceptions import ValidationError

import httpstan.schemas as schemas


def test_model_schema() -> None:
    result = schemas.Model().load({"name": "12345", "compiler_output": ""})
    assert result


def test_data_schema() -> None:
    result = schemas.Data().load({"y": [3, 2, 4]})
    assert result


def test_data_schema_invalid() -> None:
    with pytest.raises(ValidationError):
        schemas.Data().load({"y": [3, 2, 4], "p": "hello"})
