# distutils: language=c++
# cython: language_level=3
"""Wrap Stan classes and functions used by stan::services functions."""
import numpy as np

from cpython cimport pycapsule

cimport httpstan.stan as stan


def version() -> str:
    """Return Stan version."""
    return b'.'.join([stan.MAJOR_VERSION, stan.MINOR_VERSION, stan.PATCH_VERSION]).decode()


def _split_data(dict data):
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

    """
    data = data.copy()
    names_r, values_r, dim_r = [], [], []
    names_i, values_i, dim_i = [], [], []
    for k, v in data.items():
        if np.issubdtype(np.asarray(v).dtype, float):
            names_r.append(k.encode('utf-8'))
            values_r.extend(np.atleast_1d(v).astype(float))
            # TODO(AR): implement support for higher dimensional data
            if np.asarray(v).ndim > 1:
                raise NotImplementedError('Higher dimensional variables not yet supported.')
            dim_r.append(np.asarray(v).shape)
        elif np.issubdtype(np.asarray(v).dtype, np.integer):
            names_i.append(k.encode('utf-8'))
            values_i.extend(np.atleast_1d(v).astype(int))
            # TODO(AR): implement support for higher dimensional data
            if np.asarray(v).ndim > 1:
                raise NotImplementedError('Higher dimensional variables not yet supported.')
            dim_i.append(np.asarray(v).shape)
        else:
            raise ValueError(f'Variable `{k}` must be int or float.')
    return names_r, values_r, dim_r, names_i, values_i, dim_i


cdef void del_array_var_context(object obj):
    """PyCapsule destructor for ``array_var_context``."""
    cdef stan.array_var_context * var_context_ptr = <stan.array_var_context*> pycapsule.PyCapsule_GetPointer(obj, b'array_var_context')  # noqa
    del var_context_ptr


def make_array_var_context(dict data):
    """Returns a var_context PyCapsule.

    See the C++ documentation for array_var_context for details.

    """
    names_r_, values_r_, dim_r_, names_i_, values_i_, dim_i_ = _split_data(data)
    cdef vector[string] names_r = names_r_
    cdef vector[double] values_r = values_r_
    cdef vector[vector[size_t]] dim_r = dim_r_

    cdef vector[string] names_i = names_i_
    cdef vector[int] values_i = values_i_
    cdef vector[vector[size_t]] dim_i = dim_i_

    cdef stan.array_var_context * var_context = new stan.array_var_context(names_r, values_r, dim_r,
                                                                           names_i, values_i, dim_i)
    return pycapsule.PyCapsule_New(var_context, b'array_var_context', del_array_var_context)
