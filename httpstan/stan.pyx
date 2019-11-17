# distutils: language=c++
# cython: language_level=3
"""Wrap Stan classes and functions used by stan::services functions."""
cimport httpstan.stan as stan


def version() -> str:
    """Return Stan version."""
    return b'.'.join([stan.MAJOR_VERSION, stan.MINOR_VERSION, stan.PATCH_VERSION]).decode()
