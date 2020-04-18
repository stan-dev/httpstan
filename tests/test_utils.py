"""Test user-provided initial values for parameters."""
from typing import Any

import numpy as np
import pytest

import httpstan.utils


@pytest.mark.parametrize(
    "data",
    [
        {"floating_only": np.array([1.0, 2.0, 3.0], dtype=float)},
        {"integer_only": np.array([1, 2, 3], dtype=int)},
        {"floating": np.array([1.0, 2.0, 3.0], dtype=float), "integer": np.array([1, 2, 3], dtype=int)},
    ],
)
def test_data_split(data: Any) -> None:
    """Test data split."""
    names_r, values_r, dim_r, names_i, values_i, dim_i = httpstan.utils._split_data(data)
    if "floating_only" in data:
        assert b"floating_only" in names_r
        assert values_r
        assert dim_r
        assert not names_i
        assert not values_i
        assert not dim_i
    elif "integer_only" in data:
        assert not names_r
        assert not values_r
        assert not dim_r
        assert b"integer_only" in names_i
        assert values_i
        assert dim_i

    else:
        assert b"floating" in names_r
        assert values_r
        assert dim_r
        assert b"integer" in names_i
        assert values_i
        assert dim_i


def test_data_split_invalid() -> None:
    """Test data split with invalid data."""
    with pytest.raises(ValueError, match=r"Variable `x` must be int or float\."):
        httpstan.utils._split_data({"x": np.array([1, 2, 3], dtype=object)})
