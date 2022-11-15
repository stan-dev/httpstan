============
Installation
============

.. These instructions appear in both README.rst and installation.rst

**httpstan** runs on Linux and macOS. A C++ compiler is also required (gcc ≥9.0 or clang ≥10.0).

::

    $ python3 -m pip install httpstan

In order to install httpstan from PyPI make sure your system satisfies the requirements:

- Linux or macOS
- x86-64 CPU
- C++ compiler: gcc ≥9.0 or clang ≥10.0.

If your system uses a different kind of CPU, you should be able to install from source.

Installation from source
========================

Download the source code associated with a release from `https://github.com/stan-dev/httpstan/tags <https://github.com/stan-dev/httpstan/tags>`. Extract the contents of the ``zip`` or ``tar.gz`` release bundle. Alternatively, clone the git repository and checkout the commit associated with the version of httpstan you want.

Executing the following commands will build and install httpstan from source:

::

    # Build shared libraries
    make

    # Build the httpstan wheel on your system
    python3 -m pip install poetry
    python3 -m poetry build

    # Install the wheel
    python3 -m pip install dist/*.whl
