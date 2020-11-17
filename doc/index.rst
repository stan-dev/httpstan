********
httpstan
********

Release v\ |version|

An HTTP 1.1 interface to the Stan_ C++ package, **httpstan** is a shim_ that
allows users to interact with the Stan C++ library using a REST API. The
package is intended for use as a universal backend for frontends which know how
to make HTTP requests. The primary audience for this package is developers.

In addition to providing the essential functionality of the command-line interface
to Stan (CmdStan_) over HTTP, httpstan provides the following features:

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

    curl -H "Content-Type: application/json" \
        --data '{"program_code":"parameters {real y;} model {y ~ normal(0,1);}"}' \
        http://localhost:8080/v1/models

This request will return a model name along with all the compiler output::

    {"compiler_output": "In file included from …", "stanc_warnings": "", "name": "models/xc2pdjb4"}

(The model ``name`` depends on the platform and the version of Stan.)

Drawing samples from this model using default settings requires two steps: (1)
launching the sampling operation and (2) retrieving the output of the operation
(once it has finished).

First we make a request to launch the sampling operation::

    curl -H "Content-Type: application/json" \
        --data '{"function":"stan::services::sample::hmc_nuts_diag_e_adapt"}' \
        http://localhost:8080/v1/models/xc2pdjb4/fits

This request instructs ``httpstan`` to draw samples from the normal
distribution described in the model. The function name picks out a specific
function in the ``stan::services`` namespace found in the Stan C++ library (see
the Stan C++ documentation for details).  This request will return immediately
with a reference to a long-running fit operation::

    {"name": "operations/gkf54axb", "done": false, "metadata": {"fit": {"name": "models/xc2pdjb4/fits/gkf54axb"}}}

Once the operation is complete, the "fit" can be retrieved. The name of the fit,
``models/xc2pdjb4/fits/gkf54axb``, is included in the ``metadata`` field of the operation.
The fit is saved as sequence of JSON-encoded messages. These messages are strung together
with newlines. To retrieve these messages, saving them locally in the file
``myfit.bin``, make the following request::

    curl http://localhost:8080/v1/models/xc2pdjb4/fits/gkf54axb > myfit.jsonlines

The Stan "fit", saved in ``myfit.jsonlines``, aggregates all messages. By reading
them one by one you can recover all messages sent by the Stan C++ library.


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
   license
   authors
   developer_resources


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
