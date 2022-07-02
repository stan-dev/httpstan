===================
Developer Resources
===================

Notes for httpstan developers are collected here.

Updating CmdStan Sampler Parameter Defaults
===========================================

If CmdStan changes default values for arguments, pipe the output of ``modelbinary --help-all`` to a
file and then point ``scripts/parse_cmdstan_help.py`` at that file. The output
should replace the file ``httpstan/services/cmdstan-help-all.json``.

DEBUG mode
==========

If the environment variable ``HTTPSTAN_DEBUG`` is set to ``1`` or ``true``, the
call to the stan::services sampling function will block until finished instead
of being run in the background. This should make debugging crashes with ``gdb``
much easier.  There is, however, one complication. The number of samples drawn
must be set to be a very low number (e.g., ``10``) otherwise the call to the
sampling function will freeze up. The call will freeze up because the socket
used to communicate from C++ to Python will fill up. If the socket runs out of
buffer space the stan::services call will never return.

Signing key
===========
The signing key for httpstan is the same as for pystan.
The key has id ``85107A96512971B8C55932085D5D0CFF0A51A83D``.
Git tags are signed with this key.

Accounts with Continuous Integration, PyPI, and Readthedocs
===========================================================

- readthedocs: riddell-stan

Making a release of `httpstan`
==============================

The following assumes you are releasing httpstan version 4.8.0. Adjust as needed.

- Tag a release: `git tag -u 85107A96512971B8C55932085D5D0CFF0A51A83D -m "httpstan 4.8.0" 4.8.0`
- Push the tag to upstream: `git push upstream 4.8.0`
- Wait a few days, the stan-dev/httpstan-wheels repository tries to build (and publish) new wheels every two days.

If no wheels appear, check <https://github.com/stan-dev/httpstan-wheels/actions>.
