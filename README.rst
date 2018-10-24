========
httpstan
========

.. image:: https://raw.githubusercontent.com/stan-dev/logos/master/logo.png
    :alt: Stan logo
    :height: 333px
    :width: 333px
    :scale: 40 %

|pypi| |travis|

HTTP-based interface to Stan, a package for Bayesian inference.

An HTTP 1.1 interface to the Stan_ C++ package, **httpstan** is a shim_ that
allows users to interact with the Stan C++ library using an HTTP API. The
package is intended for use as a universal backend for frontends which know how
to make HTTP requests. The primary audience for this package is developers.

In addition to providing all the functionality of the command-line interface
to Stan (CmdStan_) over HTTP 1.1, **httpstan** provides:

* Automatic caching of compiled Stan models
* Automatic caching of samples from Stan models
* Parallel sampling

Documentation lives at `https://httpstan.readthedocs.org <https://httpstan.readthedocs.org>`_.

Important Disclaimer
====================
**httpstan** is experimental software. This software is not intended for general use.

httpstan currently requires Python version 3.6 or higher. No older versions of
Python will be supported.

httpstan only works on Linux and macOS. Windows support is planned.

Background
==========

**httpstan** is a shim_ allowing clients speaking HTTP to call functions in the
Stan C++ package's ``stan::services`` namespace. **httpstan** was originally
developed as a "backend" for a Python interface to Stan, PyStan_.

Install
=======

::

    python3 -m pip install httpstan

Install from Source
-------------------

A working copy of ``protoc`` is needed to build from source. One way to get this is to install
``grpcio-tools`` from PyPI with ``python3 -m pip install grpcio-tools``.

::

    make cython  # generate C++ code from Cython .pyx files
    make protos  # generate Python modules for protocol buffer schemas
    python3 setup.py install

Usage
=====

After installing ``httpstan``, running the module will begin listening on
localhost, port 8080::

    python3 -m httpstan

In a different terminal, make a POST request to
``http://localhost:8080/v1/models`` with Stan program code to compile the
program::

    curl -X POST -H "Content-Type: application/json" \
        -d '{"program_code":"parameters {real y;} model {y ~ normal(0,1);}"}' \
        http://localhost:8080/v1/models

This request will return a model name similar to the following::

    {"name": "models/89c4e75a2c"}

(The model ``name`` depends on the platform and the version of Stan.)

To draw samples from this model using default settings, we first make the
following request::

    curl -X POST -H "Content-Type: application/json" \
        -d '{"function":"stan::services::sample::hmc_nuts_diag_e_adapt"}' \
        http://localhost:8080/v1/models/89c4e75a2c/fits

This request instructs ``httpstan`` to draw samples from the normal
distribution. The function name picks out a specific function in the Stan C++
library (see the Stan C++ documentation for details).  This request will return
a fit name similar to the following::

    {"name": "models/89c4e75a2c/fits/8c10a044b6"}

The "fit" is saved as sequence of Protocol Buffer messages. These messages are strung together
using `length-prefix encoding
<https://eli.thegreenplace.net/2011/08/02/length-prefix-framing-for-protocol-buffers>`_.  To
retrieve these messages, saving them in the file ``myfit.bin``, make the following request::

    curl http://localhost:8080/v1/models/89c4e75a2c/fits/8c10a044b6 > myfit.bin

To read the messages you will need a library for reading the encoding that
Protocol Buffer messages use.  In this example we will read the first message
in the stream using the Protocol Buffer compiler tool ``protoc``. (On
Debian-based Linux you can find this tool in the ``protobuf-compiler``
package.) The following command skips the message length (one byte)
and then decodes the message (which is 48 bytes in length)::

    dd bs=1 skip=1 if=myfit.bin 2>/dev/null | head -c 48 | \
      protoc --decode stan.WriterMessage protos/callbacks_writer.proto

Running the command above decodes the first message in the stream. The
decoded message should resemble the following::

    topic: LOGGER
    feature {
      string_list {
        value: "Gradient evaluation took 1.3e-05 seconds"
      }
    }


Contribute
==========

Contribution guidelines are described in ``CONTRIBUTE.rst``.

License
=======

ISC License.

.. _shim: https://en.wikipedia.org/wiki/Shim_%28computing%29
.. _CmdStan: http://mc-stan.org/interfaces/cmdstan.html
.. _PyStan: http://mc-stan.org/interfaces/pystan.html
.. _Stan: http://mc-stan.org/
.. _`OpenAPI documentation for httpstan`: api.html

.. |pypi| image:: https://badge.fury.io/py/httpstan.png
    :target: https://badge.fury.io/py/httpstan
    :alt: pypi version

.. |travis| image:: https://travis-ci.org/stan-dev/httpstan.png?branch=master
    :target: https://travis-ci.org/stan-dev/httpstan
    :alt: travis-ci build status
