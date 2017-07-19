# distutils: language=c++
# cython: language_level=3
"""Function wrapping stan::lang::compile.

This module contains a function which wraps stan::lang::compile.
"""
from cython.operator cimport dereference as deref
cimport libcpp
from libcpp.string cimport string

cimport httpstan.lang as lang
from httpstan.libcpp cimport stringstream


def compile(program_code: str, model_name: str) -> str:
    """Return C++ code for Stan model specified by `program_code`.

    Wraps stan::lang::compile.

    Arguments:
        program_code
        model_name

    Returns:
        str: C++ code

    Raises:
        RuntimeError: C++ exception from Stan (Cython-propagated).
        ValueError: Syntax error in program code.

    """
    cdef libcpp.bool valid_program_code
    cdef stringstream out
    cdef stringstream err
    cdef stringstream program_code_stringstream
    program_code_stringstream.str(program_code.encode())
    # compile may raise C++ exception. Cython will raise it as Python exception.
    valid_program_code = lang.compile(&err, program_code_stringstream, out, model_name.encode())
    if not valid_program_code:
        error_message = err.str().encode()
        raise ValueError(f'Syntax error in program code: {error_message}')
    return out.str().decode()
