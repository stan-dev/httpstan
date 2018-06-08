# distutils: language=c++
# cython: language_level=3
cimport libcpp

# From the docs:
# "The spsc_queue class provides a single-writer/single-reader fifo queue,
# pushing and popping is wait-free."

cdef extern from "<boost/lockfree/spsc_queue.hpp>" namespace "boost::lockfree" nogil:
    cdef cppclass spsc_queue[T]:
        spsc_queue()
        spsc_queue(int)
        libcpp.bool pop(T &)
