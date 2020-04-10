===================
 Development Setup
===================

Testing a patch for httpstan is complicated due to the use of shared
libraries, code generation, and run-time compilation. Python packaging tools are not written with
this kind of use in mind.

This document is a work-in-progress. Please report any errors in these instructions.

Getting started
===============

::

    # 1. Create a virtual env
    python3 -m venv httpstan-development
    source httpstan-development/bin/activate

    # 2. Clone repository
    git clone https://github.com/stan-dev/httpstan


    # 3(a). Build shared libraries and generate code
    cd httpstan
    python3 -m pip install mypy-protobuf
    make
    python3 -m pip install poetry

    # 3(b). Install the package
    python3 -m poetry install -v

    # 4. Run tests
    python3 -m pytest -v tests

    # 5. Run code and style checks
    python3 -m pip install tox
    python3 -m tox


Troubleshooting
---------------

1. Delete cached Stan models in your cache directory (``~/.cache/httpstan`` on Linux).
2. View compiler errors by disabling stderr redirection. Edit ``models.py`` and replace ``redirect_stderr = _has_fileno(sys.stderr)`` with ``redirect_stderr = False``.
3. Try deleting any files ending in ``.so`` in the ``httpstan`` directory and then re-running ``python3 -m poetry install -v``. This should only be needed if you are editing code written in Cython.
