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

    $ make  # generate required C++ code
    $ python3 setup.py install
