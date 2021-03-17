============
Installation
============

.. These instructions appear in both README.rst and installation.rst

**httpstan** requires Python ≥ 3.7. macOS and Linux are supported. A C++ compiler is also required (gcc ≥9.0 or clang ≥10.0).

::

    $ python3 -m pip install httpstan


Installation from source
========================

These instructions are for advanced users.
The build process for httpstan is complicated and atypical.

::

    # Build shared libraries and generate code
    python3 -m pip install poetry
    make

    # Build the httpstan wheel
    python3 -m poetry build

    # Install the wheel
    python3 -m pip install dist/*.whl
