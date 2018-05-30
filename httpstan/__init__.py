"""Top-level initialization for httpstan.

Configures logging and exposes httpstan.__version__.

:license: ISC, see LICENSE for more details.
"""
import logging

import pbr.version


logging.getLogger("httpstan").addHandler(logging.NullHandler())
__version__ = pbr.version.VersionInfo("httpstan").version_string()
