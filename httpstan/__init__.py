"""Top-level initialization for httpstan.

Configures logging and exposes httpstan.__version__.

:license: ISC, see LICENSE for more details.
"""
import logging

logging.getLogger("httpstan").addHandler(logging.NullHandler())
__version__ = "4.7.0"
