:orphan:

.. _release-howto:

===============
 Release HOWTO
===============

*This document is intended for httpstan developers.*

The signing key for httpstan has id CB808C34B3BFFD03EFD2751597A78E5BFA431C9A.

Update documentation
====================

The Sphinx documentation needs to be regenerated every release::

    make apidoc

If there are any changes, commit them and create a pull request.

Tag the release
===============

- Tag (with signature): ``git tag -u CB808C34B3BFFD03EFD2751597A78E5BFA431C9A -s 0.2.5``.
- Push the new tag to the repository.

Update the ``readthedocs`` branch
=================================

There is also a `readthedocs` branch which needs to be handled separately::

    git rebase master readthedocs
    make openapi

Commit and push any changes. Readthedocs will pick up on the changes.

Update ``httpstan-wheels``
==========================

In the ``httpstan-wheels`` repository, update the version number to match the new version.

Generate source distribution and download wheels
================================================

In the root directory of the ``httpstan`` repository, run the following::

    scripts/build_dist.sh
    scripts/download_wheels.sh

Upload source distribution and wheels
=====================================

Upload source distribution and wheels::

    python3 -m twine upload --skip-existing dist/*.tar.gz dist/*.whl

If ``twine`` prompts for a username and password abort the process with
Control-C and enter your PyPI credentials in ``$HOME/.pypirc``. (For more
details see the Python documention on `the .pypirc file
<https://docs.python.org/3/distutils/packageindex.html#pypirc>`_.) Alternatively,
one can set the environment variables ``TWINE_USERNAME`` and ``TWINE_PASSWORD``.

Uploading wheels may take a long time on a low-bandwidth connection.
