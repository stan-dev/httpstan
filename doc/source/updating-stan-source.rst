:orphan:

.. _updating-stan-source:

======================
 Updating Stan Source
======================

*This document is intended for httpstan developers.*

Updating Stan source is a chore which must be done every time there is a new
release of the Stan source code.

1.	Update the Stan source by deleting all files in ``httpstan/lib/stan``.
2.	Extract the Stan release tarball to ``httpstan/lib/stan``.
3.	Extract the Stan Math release tarball to ``httpstan/lib/stan/lib/stan_math``.
