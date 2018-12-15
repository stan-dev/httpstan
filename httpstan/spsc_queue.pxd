# distutils: language=c++
# cython: language_level=3
from libcpp.string cimport string
cimport httpstan.boost as boost

cdef class SPSCQueue:
    cdef boost.spsc_queue[string] * queue_ptr  # holds pointer to spsc_queue
