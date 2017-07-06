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


def compile(program_code: str, program_name: str) -> str:
    """Return C++ code for Stan Program specified by `program_code`.

    Wraps stan::lang::compile.

    Arguments:
        program_code
        program_name

    Returns:
        str: C++ code

    Raises:
        RuntimeError: Cython-propagated C++ exception from Stan.
        ValueError: Syntax error in program code.

    """
    cdef libcpp.bool valid_program
    cdef stringstream out
    cdef stringstream err
    cdef stringstream program_code_stringstream
    program_code_stringstream.str(program_code.encode())
    # compile may raise C++ exception. Cython will raise it as Python exception.
    valid_program = lang.compile(&err, program_code_stringstream, out, program_name.encode())
    if not valid_program:
        error_message = err.str().encode()
        raise ValueError(f'Syntax error in program: {error_message}')
    return out.str().decode()
