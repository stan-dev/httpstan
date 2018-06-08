"""Compile a Stan model extension module given code written in Stan.

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

import setuptools  # noqa: see bugs.python.org/issue23114, must come before any module imports distutils
import Cython
import Cython.Build
import Cython.Build.Inline
import pkg_resources

import httpstan.compile
import httpstan.stan


def calculate_model_id(program_code: str) -> str:
    """Calculate model identifier from Stan program code.

    Identifier is a hash of the concatenation of the following:

    - UTF-8 encoded Stan program code.
    - UTF-8 encoded string recording the current Stan version.
    - UTF-8 encoded string identifying the current system platform.

    Arguments:
        program_code: Stan program code.

    Returns:
        str: hex-encoded unique identifier.

    """
    hash = hashlib.sha256(program_code.encode())
    hash.update(str(httpstan.stan.version()).encode())
    hash.update(sys.platform.encode())
    return hash.hexdigest()


def calculate_module_name(model_id: str) -> str:
    """Calculate module name from `model_id`.

    Python module names may not begin with digits. Since unique identifiers are
    often integers or hex-encoded strings, using identifiers as module names is
    not possible.

    Arguments:
        model_id

    Returns:
        str: module name derived from `model_id`.

    """
    # NOTE: must add prefix because a module name, like any variable name in
    # Python, must not begin with a number.
    return "model_{}".format(model_id)


async def compile_model_extension_module(program_code: str) -> bytes:
    """Compile extension module for a Stan model.

    Returns bytes of the compiled module.

    Since compiling a Stan model extension module takes a long time,
    compilation takes place in a different thread.

    This is a coroutine function.

    Returns:
        bytes: binary representation of module.

    """
    model_id = calculate_model_id(program_code)
    model_name = f"_{model_id}"  # C++ identifiers cannot start with digits
    cpp_code = await asyncio.get_event_loop().run_in_executor(
        None, httpstan.compile.compile, program_code, model_name
    )
    pyx_code_template = pkg_resources.resource_string(
        __name__, "anonymous_stan_model_services.pyx.template"
    ).decode()
    module_bytes = _build_extension_module(model_id, cpp_code, pyx_code_template)
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


def load_model_extension_module(model_id: str, module_bytes: bytes):
    """Load Stan model extension module from binary representation.

    This function presents a security risk! It will load a Python module which
    can execute arbitrary Python code.

    Arguments:
        model_id
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
    module_name = calculate_module_name(model_id)
    module_filename = f"{module_name}.so"
    with tempfile.TemporaryDirectory() as temporary_directory:
        with open(os.path.join(temporary_directory, module_filename), "wb") as fh:
            fh.write(module_bytes)
        module_path = temporary_directory
        assert module_name == os.path.splitext(module_filename)[0]
        return _load_module(module_name, module_path)


@functools.lru_cache()
def _build_extension_module(
    model_id: str,
    cpp_code: str,
    pyx_code_template: str,
    extra_compile_args: Optional[List[str]] = None,
) -> bytes:
    """Build extension module and return its name and binary representation.

    This returns the module name and bytes (!) of a Python extension module. The
    module is not loaded by this function.

    `cpp_code` and `pyx_code_template` are written to
    ``model_{model_id}.hpp`` and `model_{model_id}.pyx` respectively.

    The string `pyx_code_template` must contain the string ``${cpp_filename}``
    which will be replaced by ``model_{model_id}.hpp``.

    The module name is a deterministic function of its `model_id`.

    Arguments:
        model_id
        cpp_code
        pyx_code_template: string passed to ``string.Template``.
        extra_compile_args

    Returns:
        bytes: binary representation of module.

    """
    module_name = calculate_module_name(model_id)

    # write files need for compilation in a temporary directory which will be
    # removed when this function exits.
    with tempfile.TemporaryDirectory() as temporary_dir:
        cpp_filepath = os.path.join(temporary_dir, "{}.hpp".format(module_name))
        pyx_filepath = os.path.join(temporary_dir, "{}.pyx".format(module_name))
        pyx_code = string.Template(pyx_code_template).substitute(cpp_filename=cpp_filepath)
        for filepath, code in zip([cpp_filepath, pyx_filepath], [cpp_code, pyx_code]):
            with open(filepath, "w") as fh:
                fh.write(code)

        httpstan_dir = os.path.dirname(__file__)
        include_dirs = [
            httpstan_dir,  # for queue_writer.hpp and queue_logger.hpp
            temporary_dir,
            os.path.join(httpstan_dir, "lib", "stan", "src"),
            os.path.join(httpstan_dir, "lib", "stan", "lib", "stan_math"),
            os.path.join(httpstan_dir, "lib", "stan", "lib", "stan_math", "lib", "eigen_3.3.3"),
            os.path.join(httpstan_dir, "lib", "stan", "lib", "stan_math", "lib", "boost_1.66.0"),
            os.path.join(
                httpstan_dir, "lib", "stan", "lib", "stan_math", "lib", "sundials_3.1.0", "include"
            ),
        ]

        stan_macros: List[Tuple[str, Optional[str]]] = [
            ("BOOST_DISABLE_ASSERTS", None),
            ("BOOST_NO_DECLTYPE", None),
            ("BOOST_PHOENIX_NO_VARIADIC_EXPRESSION", None),
            ("BOOST_RESULT_OF_USE_TR1", None),
            ("STAN_THREADS", None),
        ]

        if extra_compile_args is None:
            if sys.platform.startswith("win"):
                extra_compile_args = ["/EHsc", "-DBOOST_DATE_TIME_NO_LIB"]
            else:
                extra_compile_args = ["-O3", "-std=c++11"]

        cython_include_path = [os.path.dirname(httpstan_dir)]
        extension = setuptools.Extension(
            module_name,
            language="c++",
            sources=[pyx_filepath],
            define_macros=stan_macros,
            include_dirs=include_dirs,
            extra_compile_args=extra_compile_args,
        )
        build_extension = Cython.Build.Inline._get_build_extension()
        build_extension.extensions = Cython.Build.cythonize(
            [extension], include_path=cython_include_path
        )
        build_extension.build_temp = build_extension.build_lib = temporary_dir

        # TODO(AR): wrap stderr, return it as well
        build_extension.run()

        module = _load_module(module_name, build_extension.build_lib)
        with open(module.__file__, "rb") as fh:  # type: ignore  # pending fix, see mypy#3062
            assert module.__name__ == module_name, (module.__name__, module_name)
            return fh.read()  # type: ignore  # pending fix, see mypy#3062
