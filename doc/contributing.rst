========================
Contributing to httpstan
========================

**httpstan** is a shim_ allowing clients able to make HTTP-based requests to
call functions in the Stan C++ library's ``stan::services`` namespace.
**httpstan** was originally developed as a "backend" for a Stan interface
written in Python, PyStan_.

Goals:

- Provide access to frequently-used functions in Stan C++ library's ``stan::services`` namespace.
- Minimize toil. Maintaining httpstan should require as little time as possible.

Non-goals:

- Provide access to functions other than those in the ``stan::services`` namespace.
  There are only three exceptions to this non-goal: ``model_base_crtp.log_prob``,
  ``model_base_crtp.write_array``, and ``stan::model::log_prob_grad``.

If these goals and non-goals strike you as restrictive, we kindly remind you
that httpstan is open source software which you are free to fork and customize.

.. _shim: https://en.wikipedia.org/wiki/Shim_%28computing%29
.. _PyStan: http://mc-stan.org/interfaces/pystan.html

How to Make a Code Contribution
===============================

Code contributions must be readable and easy to understand.
httpstan emerged out of a rewrite of an existing piece of software (PyStan)
which was difficult to maintain. httpstan aims to be maintainable.

See `Contributing to PyStan`_ in the PyStan repository. Contributions
to httpstan follow the same guidelines.

There is one important difference between httpstan and PyStan.
httpstan provides access to Stan functions via an HTTP-based REST API.
This REST API follows the conventions described in the document `API Design Guide
<https://cloud.google.com/apis/design/>`_.

.. _Contributing to PyStan: https://pystan-next.readthedocs.io/en/latest/contributing.html
