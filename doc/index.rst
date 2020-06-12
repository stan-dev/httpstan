********
httpstan
********

Release v\ |version|

An HTTP 1.1 interface to the Stan_ C++ package, **httpstan** is a shim_ that
allows users to interact with the Stan C++ library using a REST API. The
package is intended for use as a universal backend for frontends which know how
to make HTTP requests. The primary audience for this package is developers.

In addition to providing the essential functionality of the command-line interface
to Stan (CmdStan_) over HTTP, **httpstan** provides the following features:

* Automatic caching of compiled Stan models
* Automatic caching of samples from Stan models
* Parallel sampling

Usage
=====

After installing ``httpstan``, running the module will begin listening on
localhost, port 8080::

    python3 -m httpstan

An HTTP-based REST API is now available with the endpoint: `<http://localhost:8080/v1/>`_. The page
:doc:`rest_api` has a complete description of the resources available.

In a different terminal, make a POST request to
``http://localhost:8080/v1/models`` with Stan program code to compile the
program::

    curl -X POST -H "Content-Type: application/json" \
        -d '{"program_code":"parameters {real y;} model {y ~ normal(0,1);}"}' \
        http://localhost:8080/v1/models

This request will return a model name along with all the compiler output::

    {"name": "models/89c4e75a2c", "compiler_output": "..."}

(The model ``name`` depends on the platform and the version of Stan.)

Drawing samples from this model using default settings requires two steps: (1)
launching the sampling operation and (2) retrieving the output of the operation
(once it has finished).

First we make a request to launch the sampling operation::

    curl -X POST -H "Content-Type: application/json" \
        -d '{"function":"stan::services::sample::hmc_nuts_diag_e_adapt"}' \
        http://localhost:8080/v1/models/e1ca9f7ac7/fits

This request instructs ``httpstan`` to draw samples from the normal
distribution described in the model. The function name picks out a specific
function in the ``stan::services`` namespace found in the Stan C++ library (see
the Stan C++ documentation for details).  This request will return immediately
with a reference to a long-running fit operation::

    {"done": false, "name": "operations/9f9d701294", "metadata": {"fit": {"name": "models/e1ca9f7ac7/fits/9f9d701294"}}}

Once the operation is complete, the "fit" can be retrieved. The name of the fit,
``models/e1ca9f7ac7/fits/9f9d701294``, is included in the ``metadata`` field of the operation.
The fit is saved as sequence of Protocol Buffer messages. These messages are strung together
using `length-prefix encoding
<https://eli.thegreenplace.net/2011/08/02/length-prefix-framing-for-protocol-buffers>`_.  To
retrieve these messages, saving them locally in the file ``myfit.bin``, make the following request::

    curl http://localhost:8080/v1/models/e1ca9f7ac7/fits/9f9d701294 > myfit.bin

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

Citation
========

We appreciate citations as they let us discover what people have been doing
with the software. Citations also provide evidence of use which can help in
obtaining grant funding.

Allen Riddell, and Ari Hartikainen. 2019. Stan-Dev/Httpstan: V1.0.0. *Zenodo*. `<https://doi.org/10.5281/zenodo.3546351>`_.


User Guide
==========

.. Note: httpstan.rst and related API docs are generated with sphinx-apidoc

.. toctree::
   :maxdepth: 1

   installation
   rest_api
   autoapi/index
   contributing
   development_setup
   authors
   license
   developers


.. _shim: https://en.wikipedia.org/wiki/Shim_%28computing%29
.. _CmdStan: http://mc-stan.org/interfaces/cmdstan.html
.. _PyStan: http://mc-stan.org/interfaces/pystan.html
.. _Stan: http://mc-stan.org/
.. _`OpenAPI documentation for httpstan`: api.html

.. |pypi| image:: https://badge.fury.io/py/httpstan.png
    :target: https://badge.fury.io/py/httpstan
    :alt: pypi version

.. |actions| image:: https://github.com/stan-dev/httpstan/workflows/httpstan/badge.svg?branch=master
    :target: https://github.com/stan-dev/httpstan/actions
    :alt: actions-ci build status

.. |coveralls| image:: https://coveralls.io/repos/github/stan-dev/httpstan/badge.svg?branch=master
    :target: https://coveralls.io/github/stan-dev/httpstan?branch=master
    :alt: test coverage report
