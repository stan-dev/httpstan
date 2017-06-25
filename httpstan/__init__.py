"""Top-level initialization for httpstan.

Configures logging and exposes httpstan.__version__.

:license: ISC, see LICENSE for more details.
"""
import logging

import pbr.version


logger = logging.getLogger('httpstan')
logger.addHandler(logging.NullHandler())
if len(logger.handlers) == 1:
    logging.basicConfig(level=logging.INFO)


__version__ = pbr.version.VersionInfo('httpstan').version_string()
