"""Top-level initialization for httpstan.

Configures logging and exposes httpstan.__version__.

:license: ISC, see LICENSE for more details.
"""
import importlib.metadata
import logging

logging.getLogger("httpstan").addHandler(logging.NullHandler())

# try-except allows mypy to run without httpstan being installed
try:
    __version__ = importlib.metadata.version("httpstan")
except importlib.metadata.PackageNotFoundError:
    pass
