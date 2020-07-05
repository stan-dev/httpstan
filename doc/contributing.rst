========================
Contributing to httpstan
========================

**httpstan** is a shim_ allowing clients able to make HTTP-based requests to
call functions in the Stan C++ library's ``stan::services`` namespace.
**httpstan** was originally developed as a "backend" for a Stan interface
written in Python, PyStan_.

httpstan emerged out of a rewrite of an existing piece of software (PyStan)
which was difficult to maintain. httpstan aims to be maintainable. Code
contributions should be readable and easy to understand.

.. _shim: https://en.wikipedia.org/wiki/Shim_%28computing%29
.. _PyStan: http://mc-stan.org/interfaces/pystan.html

How to Make a Code Contribution
===============================

See `Contributing to PyStan`_ in the PyStan repository. Contributions
to httpstan follow the same guidelines.

There is one important difference between httpstan and pystan.
httpstan provides an HTTP-based REST API.
This REST API follows the conventions described in the document `API Design Guide
<https://cloud.google.com/apis/design/>`_. Contributors interested in changing
the behavior of the REST API should consult this document.

.. _Contributing to PyStan: https://pystan-next.readthedocs.io/en/latest/contributing.html
