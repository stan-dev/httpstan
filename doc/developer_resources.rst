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
The signing key for httpstan has id ``CB808C34B3BFFD03EFD2751597A78E5BFA431C9A``. Git tags are signed with this key

Accounts with Continuous Integration, PyPI, and Readthedocs
===========================================================

- readthedocs: riddell-stan
