# distutils: language=c++
# cython: language_level=3
"""Wrap Stan classes and functions used by stan::services functions."""
from cpython cimport pycapsule
import numpy as np

cimport httpstan.stan as stan
import httpstan.utils


def version() -> str:
    """Return Stan version."""
    return b'.'.join([stan.MAJOR_VERSION, stan.MINOR_VERSION, stan.PATCH_VERSION]).decode()


cdef void del_array_var_context(object obj):
    """PyCapsule destructor for ``array_var_context``."""
    cdef stan.array_var_context * var_context_ptr = <stan.array_var_context*> pycapsule.PyCapsule_GetPointer(obj, b'array_var_context')  # noqa
    del var_context_ptr


def make_array_var_context(dict data):
    """Returns a var_context PyCapsule.

    See the C++ documentation for array_var_context for details.

    """
    names_r_, values_r_, dim_r_, names_i_, values_i_, dim_i_ = httpstan.utils._split_data(data)
    cdef vector[string] names_r = names_r_
    cdef vector[double] values_r = values_r_
    cdef vector[vector[size_t]] dim_r = dim_r_

    cdef vector[string] names_i = names_i_
    cdef vector[int] values_i = values_i_
    cdef vector[vector[size_t]] dim_i = dim_i_

    cdef stan.array_var_context * var_context = new stan.array_var_context(names_r, values_r, dim_r,
                                                                           names_i, values_i, dim_i)
    capsule = pycapsule.PyCapsule_New(var_context, b'array_var_context', del_array_var_context)
    assert pycapsule.PyCapsule_IsValid(capsule, b'array_var_context')
    return capsule


def _array_var_context_contains(str name, object array_var_context_capsule):
    """Check if `name` is associated with an array_var_context (capsule).

    Used in tests.

    """
    cdef stan.array_var_context * var_context_ptr = <stan.array_var_context*> pycapsule.PyCapsule_GetPointer(array_var_context_capsule, b'array_var_context')
    assert pycapsule.PyCapsule_IsValid(array_var_context_capsule, b'array_var_context')
    return var_context_ptr.contains_r(name.encode('utf-8')) or var_context_ptr.contains_i(name.encode('utf-8'))
