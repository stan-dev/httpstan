"""Test HTTP views and related functions."""
import httpstan.views as views


def test_make_error() -> None:
    message, details = "Error message", [{"metadata": "some metadata"}, {"key": "value"}]
    status_dict = views._make_error(message, 500, details=details)
    assert status_dict["message"] == message
    assert status_dict["details"] == details
