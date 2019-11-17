============
Installation
============

.. These instructions occuring in both README.rst and installation.rst

**httpstan** requires Python >= 3.6.  macOS and Linux are supported, Windows is not (currently).

At the command line::

    $ python3 -m pip install httpstan

Install from Source
-------------------

::

    $ python3 -m pip install -r build-requirements.txt
    $ make  # generate required C++ code
    $ python3 setup.py install

