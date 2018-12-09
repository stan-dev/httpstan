============
Installation
============

At the command line::

::

    $ python3 -m pip install httpstan

Install from Source
-------------------

A working copy of ``protoc`` is needed to build from source. An easy way to install `protoc` is to install ``grpcio-tools`` from PyPI with ``python3 -m pip install grpcio-tools``.

::

    $ make cython  # generate C++ code from Cython .pyx files
    $ make protos  # generate Python modules for protocol buffer schemas
    $ python3 setup.py install
