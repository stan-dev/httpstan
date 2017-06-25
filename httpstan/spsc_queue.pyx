# distutils: language=c++
# cython: language_level=3
"""Wrap Boost's lock-free single-producer/single-consumer queue.

The interface modifies Boost's interface slightly in order to match the
interface provided by Python's queue.Queue (part of the Python standard
library).
"""
import queue

cimport cpython
cimport libcpp
from libcpp.string cimport string

cimport httpstan.boost as boost


cdef class SPSCQueue:
    """Python interface to spsc_queue[string].

    Interface only exposes methods for retrieving data.

    See boost documentation for spsc_queue for more information.

    """
    cdef boost.spsc_queue[string] * queue_ptr  # holds pointer to spsc_queue

    def __cinit__(self, int capacity):
        self.queue_ptr = new boost.spsc_queue[string](capacity)

    def get_nowait(self):
        """Mimics the interface of Python's queue.Queue's get_nowait."""
        cdef string message
        if self.queue_ptr.pop(message):
            return message
        else:
            raise queue.Empty

    def to_capsule(self):
        """Create a PyCapsule of the pointer to spsc_queue.

        No destructor function passed here since __dealloc__ does this work.

        """
        return cpython.PyCapsule_New(self.queue_ptr, b'spsc_queue', NULL)

    def __dealloc__(self):
        del self.queue_ptr
