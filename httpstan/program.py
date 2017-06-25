"""Compile a Stan Program extension module given code written in Stan.

These functions manage the process of compiling a Python extension module
from C++ code generated and loading the resulting module.
"""
import asyncio
import functools
import hashlib
import importlib
import os
import string
import sys
import tempfile
from typing import List
from typing import Optional
from typing import Tuple  # noqa: flake8 bug, #118

import Cython
import Cython.Build
import Cython.Build.Inline
import distutils
import distutils.extension

import httpstan.compile
import httpstan.stan


def calculate_program_id(program_code: str) -> str:
    """Calculate program identifier from Stan program code.

    Identifier is a hash of the concatenation of the following:

    - UTF-8 encoded Stan Program written in the Stan language
    - UTF-8 encoded string recording the current Stan version.
    - UTF-8 encoded string identifying the current system platform

    Arguments:
        program_code: Stan Program code.

    Returns:
        str: hex-encoded unique identifier.

    """
    hash = hashlib.sha256(program_code.encode())
    hash.update(str(httpstan.stan.version()).encode())
    hash.update(sys.platform.encode())
    return hash.hexdigest()


def calculate_module_name(program_id: str) -> str:
    """Calculate module name from `program_id`.

    Python module names may not begin with digits. Since unique identifiers are
    often integers or hex-encoded strings, using identifiers as module names is
    not possible.

    Arguments:
        program_id

    Returns:
        str: module name derived from `program_id`.

    """
    # NOTE: must add prefix because a module name, like any variable name in
    # Python, must not begin with a number.
    return 'program_{}'.format(program_id)


async def compile_program_extension_module(program_code: str) -> bytes:
    """Compile extension module for a Stan Program.

    Returns bytes of the compiled module.

    Since compiling a Stan Program extension module takes a long time,
    compilation takes place in a different thread.

    This is a coroutine function.

    Returns:
        bytes: binary representation of module.

    """
    program_id = calculate_program_id(program_code)
    program_name = f'_{program_id}'  # C++ identifiers cannot start with digits
    cpp_code = await asyncio.get_event_loop().run_in_executor(None, httpstan.compile.compile,
                                                              program_code, program_name)
    # TODO(AR): get this file via pkg_resources
    with open(os.path.join(os.path.dirname(__file__), 'anonymous_stan_program_services.pyx.template')) as fh:
        pyx_code_template = fh.read()
    module_bytes = _build_extension_module(program_id, cpp_code, pyx_code_template)
    return module_bytes


def _load_module(module_name: str, module_path: str):
    """Load the module named `module_name` from  `module_path`.

    Arguments:
        module_name: module name.
        module_path: module path.

    Returns:
        module: Loaded module.

    """
    sys.path.append(module_path)
    module = importlib.import_module(module_name)
    sys.path.pop()
    return module


def load_program_extension_module(program_id: str, module_bytes: bytes):
    """Load Stan Program extension module from binary representation.

    This function presents a security risk! It will load a Python module which
    can execute arbitrary Python code.

    Arguments:
        program_id
        module_bytes

    Returns:
        module: loaded module handle.

    """
    # TODO(AR): This function is a security risk! Bytes should be authenticated.
    # In principle this should be easy to do because httpstan will only ever
    # load modules that it has itself produced.

    # NOTE: module suffix can be '.so'; does not need to be, say,
    # '.cpython-36m-x86_64-linux-gnu.so'.  The module's filename (minus any
    # suffix) does matter: Python calls an initialization function using the
    # module name, e.g., PyInit_mymodule.  Filenames which do not match the name
    # of this function will not load.
    module_name = calculate_module_name(program_id)
    module_filename = f'{module_name}.so'
    with tempfile.TemporaryDirectory() as temporary_directory:
        with open(os.path.join(temporary_directory, module_filename), 'wb') as fh:
            fh.write(module_bytes)
        module_path = temporary_directory
        assert module_name == os.path.splitext(module_filename)[0]
        return _load_module(module_name, module_path)


@functools.lru_cache()
def _build_extension_module(program_id: str, cpp_code: str, pyx_code_template: str,
                            extra_compile_args: Optional[List[str]] = None) -> bytes:
    """Build extension module and return its name and binary representation.

    This returns the module name and bytes (!) of a Python extension module. The
    module is not loaded by this function.

    `cpp_code` and `pyx_code_template` are written to
    ``program_{program_id}.hpp`` and `program_{program_id}.pyx` respectively.

    The string `pyx_code_template` must contain the string ``${cpp_filename}``
    which will be replaced by ``program_{program_id}.hpp``.

    The module name is a deterministic function of its `program_id`.

    Arguments:
        program_id
        cpp_code
        pyx_code_template: string passed to ``string.Template``.
        extra_compile_args

    Returns:
        bytes: binary representation of module.

    """
    module_name = calculate_module_name(program_id)

    # write files need for compilation in a temporary directory which will be
    # removed when this function exits.
    with tempfile.TemporaryDirectory() as temporary_dir:
        cpp_filepath = os.path.join(temporary_dir, '{}.hpp'.format(module_name))
        pyx_filepath = os.path.join(temporary_dir, '{}.pyx'.format(module_name))
        pyx_code = string.Template(pyx_code_template).substitute(cpp_filename=cpp_filepath)
        for filepath, code in zip([cpp_filepath, pyx_filepath], [cpp_code, pyx_code]):
            with open(filepath, 'w') as fh:
                fh.write(code)

        httpstan_dir = os.path.dirname(__file__)
        include_dirs = [
            httpstan_dir,  # for queue_writer.hpp and queue_logger.hpp
            temporary_dir,
            os.path.join(httpstan_dir, 'lib', 'stan', 'src'),
            os.path.join(httpstan_dir, 'lib', 'stan', 'lib', 'stan_math'),
            os.path.join(httpstan_dir, 'lib', 'stan', 'lib', 'stan_math', 'lib', 'eigen_3.3.3'),
            os.path.join(httpstan_dir, 'lib', 'stan', 'lib', 'stan_math', 'lib', 'boost_1.62.0'),
            os.path.join(httpstan_dir, 'lib', 'stan', 'lib', 'stan_math', 'lib', 'cvodes_2.9.0', 'include'),
        ]

        stan_macros: List[Tuple[str, Optional[str]]] = [
            ('BOOST_RESULT_OF_USE_TR1', None),
            ('BOOST_NO_DECLTYPE', None),
            ('BOOST_DISABLE_ASSERTS', None),
        ]

        if extra_compile_args is None:
            if sys.platform.startswith('win'):
                extra_compile_args = ['/EHsc', '-DBOOST_DATE_TIME_NO_LIB']
            else:
                extra_compile_args = [
                    '-O3',
                    '-std=c++11',
                ]

        build_extension = Cython.Build.Inline._get_build_extension()

        cython_include_path = [os.path.dirname(httpstan_dir)]
        extension = distutils.extension.Extension(module_name,
                                                  language='c++',
                                                  sources=[pyx_filepath],
                                                  define_macros=stan_macros,
                                                  include_dirs=include_dirs,
                                                  extra_compile_args=extra_compile_args)
        build_extension.extensions = Cython.Build.cythonize([extension],
                                                            include_path=cython_include_path)
        build_extension.build_temp = build_extension.build_lib = temporary_dir

        # TODO(AR): wrap stderr, return it as well
        build_extension.run()

        module = _load_module(module_name, build_extension.build_lib)
        with open(module.__file__, 'rb') as fh:
            assert module.__name__ == module_name, (module.__name__, module_name)
            return fh.read()
