===================
 Development Setup
===================

Testing a patch for httpstan is complicated due to the heavy use of shared
libraries and dynamic compilation. Python packaging tools are not written with
this kind of use in mind.

This document is a work-in-progress. Please report any errors in these instructions.

Getting started
===============

::

    # first, install the protobuf compiler `protoc`
    python3 -m venv httpstan-development
    source httpstan-development/bin/activate
    git clone https://github.com/stan-dev/httpstan
    cd httpstan
    python3 -m pip install mypy-protobuf
    make
    python3 -m pip install poetry
    python3 -m poetry install -v
    # finally, run tests
    python3 -m pytest -v tests
    # run linters
    python3 -m tox


Troubleshooting
---------------

1. Delete cached Stan models in your cache directory (``~/.cache/httpstan`` on Linux).
2. View compiler errors by disabling stderr redirection. Edit ``models.py`` and replace ``redirect_stderr = _has_fileno(sys.stderr)`` with ``redirect_stderr = False``.
3. Try deleting any files ending in ``.so`` in the ``httpstan`` directory and then re-running ``python3 -m poetry install -v``. This should only be needed if you are editing code written in Cython.
