============
Installation
============

.. These instructions appear in both README.rst and installation.rst

**httpstan** requires Python ≥ 3.7. macOS and Linux are supported.

::

    $ python3 -m pip install httpstan


Installation from source
========================

These instructions are for advanced users.
The build process for httpstan is not simple.

::

    # 1. Create a virtual env
    python3 -m venv httpstan-development
    source httpstan-development/bin/activate

    # 2. Clone repository
    git clone https://github.com/stan-dev/httpstan

    # 3. Build shared libraries and generate code
    cd httpstan
    python3 -m pip install mypy-protobuf==1.21 Cython poetry
    make

    # 4. Build the httpstan wheel
    python3 -m poetry build

    # 5. Install the wheel
    python3 -m pip install dist/*.whl
