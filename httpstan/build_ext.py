"""Lightly modified build_ext which captures stderr.

isort:skip_file
"""

# IMPORTANT: `import setuptools` MUST come before any module imports `distutils`
# background: https://bugs.python.org/issue23102
import setuptools  # noqa: F401

import setuptools._distutils.command.build_ext as build_ext
import setuptools._distutils.core
import io
import os
import sys
import tempfile
from typing import IO, Any, List, TextIO

from httpstan.config import HTTPSTAN_DEBUG


def _get_build_extension() -> build_ext.build_ext:  # type: ignore
    if HTTPSTAN_DEBUG:  # pragma: no cover
        setuptools._distutils.log.set_verbosity(setuptools._distutils.log.DEBUG)  # type: ignore
    dist = setuptools._distutils.core.Distribution()
    # Make sure build respects distutils configuration
    dist.parse_config_files(dist.find_config_files())  # type: ignore
    build_extension = build_ext.build_ext(dist)  # type: ignore
    build_extension.finalize_options()
    return build_extension


def run_build_ext(extensions: List[setuptools._distutils.core.Extension], build_lib: str) -> str:
    """Configure and call `build_ext.run()`, capturing stderr.

    Compiled extension module will be placed in `build_lib`.

    All messages sent to stderr will be saved and returned. These
    messages are typically messages from the compiler or linker.

    """

    # utility functions for silencing compiler output
    def _has_fileno(stream: TextIO) -> bool:
        """Returns whether the stream object has a working fileno()

        Suggests whether _redirect_stderr is likely to work.
        """
        try:
            stream.fileno()
        except (AttributeError, OSError, IOError, io.UnsupportedOperation):  # pragma: no cover
            return False
        return True

    def _redirect_stderr_to(stream: IO[Any]) -> int:
        """Redirect stderr for subprocesses to /dev/null.

        Returns
        -------
        orig_stderr: copy of original stderr file descriptor
        """
        sys.stderr.flush()
        stderr_fileno = sys.stderr.fileno()
        orig_stderr = os.dup(stderr_fileno)
        os.dup2(stream.fileno(), stderr_fileno)
        return orig_stderr

    build_extension = _get_build_extension()
    build_extension.build_lib = build_lib

    # silence stderr for compilation, if stderr is silenceable
    stream = tempfile.TemporaryFile(prefix="httpstan_")
    redirect_stderr = _has_fileno(sys.stderr) and not HTTPSTAN_DEBUG
    compiler_output = ""
    if redirect_stderr:
        orig_stderr = _redirect_stderr_to(stream)

    build_extension.extensions = extensions

    try:
        build_extension.run()
    finally:
        if redirect_stderr:
            stream.seek(0)
            compiler_output = stream.read().decode()
            stream.close()
            # restore
            os.dup2(orig_stderr, sys.stderr.fileno())

    return compiler_output
