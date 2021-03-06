"""Test Schema validation."""
import pytest
from marshmallow.exceptions import ValidationError

import httpstan.schemas as schemas


def test_model_schema() -> None:
    result = schemas.Model().load({"name": "12345", "compiler_output": "", "stanc_warnings": ""})
    assert result


def test_data_schema() -> None:
    result = schemas.Data().load({"y": [3, 2, 4]})
    assert result


def test_data_schema_invalid() -> None:
    with pytest.raises(ValidationError):
        schemas.Data().load({"y": [3, 2, 4], "p": "hello"})


def test_writer_message_schema_mapping() -> None:
    payload = {
        "version": 1,
        "topic": "sample",
        "values": {
            "divergent__": 0,
            "lp__": -0.259381,
            "y": 0.720251,
        },
    }
    result = schemas.WriterMessage().load(payload)
    assert result


def test_writer_message_schema_list() -> None:
    payload = {
        "version": 1,
        "topic": "sample",
        "values": ["a", "b", "c"],
    }
    result = schemas.WriterMessage().load(payload)
    assert result


def test_writer_message_schema_invalid_missing_field() -> None:
    payload = {
        "version": 1,
        # missing "topic"
        "values": ["a", "b", "c"],
    }
    with pytest.raises(ValidationError):
        schemas.WriterMessage().load(payload)


def test_writer_message_schema_invalid_extra_field() -> None:
    payload = {
        "version": 1,
        "topic": "sample",
        "values": ["a", "b", "c"],
        "extra_field": 3,
    }
    with pytest.raises(ValidationError):
        schemas.WriterMessage().load(payload)
