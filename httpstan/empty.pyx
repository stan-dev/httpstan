# distutils: language=c++
# cython: language_level=3
"""Empty extension module.

This module contains a single no-op function. It is compiled so that the wheel
machinery recognizes the wheel as being a platform-specific wheel.

"""

def noop() -> None:
    pass
