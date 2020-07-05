===================
Developer Resources
===================

Notes for httpstan developers are collected here.

Updating CmdStan Sampler Parameter Defaults
===========================================

If CmdStan changes default values for arguments, pipe the output of ``modelbinary --help-all`` to a
file and then point ``scripts/parse_cmdstan_help.py`` at that file. The output
should replace the file ``httpstan/services/cmdstan-help-all.json``.

Signing key
===========
The signing key for httpstan has id ``CB808C34B3BFFD03EFD2751597A78E5BFA431C9A``. Git tags are signed with this key

Accounts with Continuous Integration, PyPI, and Readthedocs
===========================================================

- readthedocs: riddell-stan
