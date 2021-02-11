"""Miscellaneous helper routines."""
from typing import Tuple  # noqa: flake8 bug, #118
from typing import List

import numpy as np


def _split_data(
    data: dict,
) -> Tuple[List[str], List[float], List[Tuple[int, ...]], List[str], List[int], List[Tuple[int, ...]]]:
    """Prepare data for use in an array_var_context constructor.

    array_var_context is a C++ class defined in Stan. See
    ``array_var_context.hpp`` for details.

    The constructor signature is::

        array_var_context(const std::vector<std::string>& names_r,
                          const std::vector<double>& values_r,
                          const std::vector<std::vector<size_t> >& dim_r,
                          const std::vector<std::string>& names_i,
                          const std::vector<int>& values_i,
                          const std::vector<std::vector<size_t> >& dim_i)

    Multi-dimensional data is flattened using column-major order when passed to
    ``array_var_context``. Stan uses column-major order. Numpy, by constrast,
    uses row-major order by default. To unravel a multi-dimensional array using
    column-major order using numpy indicate order `F` ('F' stands for Fortran).

    Arguments:
        data: Mapping of names to values (e.g., {'y': [0, 1, 2]}).

    Returns:
        Arguments with types matching the signature of ``array_var_context``.

    """
    data = data.copy()

    names_r: List[str] = []
    values_r: List[float] = []
    dim_r: List[Tuple[int, ...]] = []

    names_i: List[str] = []
    values_i: List[int] = []
    dim_i: List[Tuple[int, ...]] = []

    for k, v in data.items():
        if np.issubdtype(np.asarray(v).dtype, np.floating):
            names_r.append(k.encode("utf-8"))
            # unravel multi-dimensional arrays using column-major ('F') order
            values_r.extend(np.atleast_1d(v).ravel(order="F").astype(float))
            dim_r.append(np.asarray(v).shape)
        elif np.issubdtype(np.asarray(v).dtype, np.integer):
            names_i.append(k.encode("utf-8"))
            # unravel multi-dimensional arrays using column-major ('F') order
            values_i.extend(np.atleast_1d(v).ravel(order="F").astype(int))
            dim_i.append(np.asarray(v).shape)
        else:
            raise ValueError(f"Variable `{k}` must be int or float.")
    return names_r, values_r, dim_r, names_i, values_i, dim_i
