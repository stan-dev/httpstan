========
httpstan
========

.. image:: https://raw.githubusercontent.com/stan-dev/logos/master/logo.png
    :alt: Stan logo
    :height: 333px
    :width: 333px
    :scale: 40 %

|pypi| |travis|

HTTP interface to Stan, a package for Bayesian inference.

An HTTP 1.1 interface to the Stan_ C++ package, **httpstan** is a shim_ that
allows users to interact with the Stan C++ library using a `Web API`_. The
package is intended for use as a universal backend for frontends which know how
to make HTTP requests. The primary audience for this package is developers.

In addition to providing all the functionality of the command-line interface
to Stan (CmdStan_) over HTTP 1.1, **httpstan** provides:

* Automatic caching of compiled Stan models
* Automatic caching of samples from Stan models
* Parallel sampling

Important Disclaimer
====================
**httpstan** is experimental software. This software is not intended for general use.

httpstan currently requires Python 3.6 as it uses asynchronous generators (PEP525). Support for
Python 3.5 may emerge at some point. No older versions of Python will be supported.

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

::

    make cython  # genreate C++ code from Cython .pyx files
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

This request will return a model id similar to the following::

    {"model": {"id": "8137474d19926b0aa8efd4f1d3944131d59269d97a7bd8dab8e79d667eb314df"}}

(The model ``id`` will be different on different platforms and with different versions of Stan.)

To draw samples from this model using default settings, we make the following request::

    curl -X POST -H "Content-Type: application/json" \
        -d '{"type":"stan::services::sample::hmc_nuts_diag_e_adapt"}' \
        http://localhost:8080/v1/models/8137474d19926b0aa8efd4f1d3944131d59269d97a7bd8dab8e79d667eb314df/actions

This request will return samples from the normal distribution. The output is
taken directly from the output of the relevant function defined in the Stan C++
package. Consult the Stan C++ documentation for details.

Contribute
==========

Contribution guidelines are described in ``CONTRIBUTE.rst``.

License
=======

ISC License.

.. _shim: https://en.wikipedia.org/wiki/Shim_%28computing%29
.. _`Web API`: https://en.wikipedia.org/wiki/Web_API
.. _CmdStan: http://mc-stan.org/interfaces/cmdstan.html
.. _PyStan: http://mc-stan.org/interfaces/pystan.html
.. _Stan: http://mc-stan.org/
.. _`OpenAPI documentation for httpstan`: api.html
.. _bash: https://en.wikipedia.org/wiki/Bash_%28Unix_shell%29

.. |pypi| image:: https://badge.fury.io/py/httpstan.png
    :target: https://badge.fury.io/py/httpstan
    :alt: pypi version

.. |travis| image:: https://travis-ci.org/stan-dev/httpstan.png?branch=master
    :target: https://travis-ci.org/stan-dev/httpstan
    :alt: travis-ci build status
