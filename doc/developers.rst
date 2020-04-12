===================
Developer Resources
===================

Notes for httpstan developers are collected here:

The signing key for httpstan has id ``CB808C34B3BFFD03EFD2751597A78E5BFA431C9A``.

How to make a release
=====================

- Verify that the correct version is shown in ``pyproject.toml``, ``httpstan/__init__.py``, and ``tests/test_httpstan.py``.
- Update ``CHANGELOG.rst``. Create Pull Request. Wait for PR to be merged.
- Verify release does not break pystan. Build the wheel locally using ``python3 -m poetry build``, create a venv, install the wheel, install pystan, run pystan's tests.
- Tag (with signature): ``git tag -u CB808C34B3BFFD03EFD2751597A78E5BFA431C9A -s 1.2.3``, replacing ``1.2.3`` with the version.
- Push the new tag to the repository: ``git push origin 1.2.3``, replacing ``origin`` with the remote and ``1.2.3`` with the version.
- In the ``httpstan-wheels`` repository, update the version number to match the new version.

Updating CmdStan Sampler Parameter Defaults
===========================================

If CmdStan changes the defaults, pipe the output of ``modelbinary --help-all`` to a
file and then point ``scripts/parse_cmdstan_help.py`` at that file. The output
should replace the file ``httpstan/services/cmdstan-help-all.json``.

Building Documentation
======================

::

    python3 -m sphinx -T -W doc build/html

Accounts with Continuous Integration, PyPI, and Readthedocs
===========================================================

- readthedocs: riddell-stan
