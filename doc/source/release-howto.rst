===============
 Release HOWTO
===============

*This document is intended for httpstan developers.*

The signing key for httpstan has id CB808C34B3BFFD03EFD2751597A78E5BFA431C9A.

The instructions below assume the following have already taken place:

- The new release has been tagged (with signature) in the ``httpstan`` repository with: ``git tag -u CB808C34B3BFFD03EFD2751597A78E5BFA431C9A -s 0.2.5``.
- The ``httpstan-wheels`` repository has been updated to build wheels for the new release. Wheels will be built after this update.

Generate source distribution and download wheels
================================================

In the root directory of the ``httpstan`` repository, run the following::

    scripts/build_dist.sh
    scripts/download_wheels.sh

Sign and upload source distribution and wheels
==============================================

Sign source distribution and wheels::

    for filename in dist/*{.tar.gz,.whl}; do
        gpg --detach-sign -a -u CB808C34B3BFFD03EFD2751597A78E5BFA431C9A "$filename"
    done

Upload source distribution and wheels::

    python3 -m twine upload --skip-existing dist/*.tar.gz dist/*.tar.gz.asc dist/*.whl dist/*.whl.asc

If ``twine`` prompts for a username and password abort the process with
Control-C and enter your PyPI credentials in ``$HOME/.pypirc``. (For more
details see the Python documention on `the .pypirc file
<https://docs.python.org/3/distutils/packageindex.html#pypirc>`_.) Alternatively,
one can set the environment variables ``TWINE_USERNAME`` and ``TWINE_PASSWORD``.

Uploading wheels may take a long time on a low-bandwidth connection.
