"""Top-level initialization for httpstan.

Configures logging and exposes httpstan.__version__.

:license: ISC, see LICENSE for more details.
"""
import logging

logging.getLogger("httpstan").addHandler(logging.NullHandler())

try:
    from importlib.metadata import version

    __version__ = version("httpstan")
except ModuleNotFoundError:
    pass
