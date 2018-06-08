# distutils: language=c++
# cython: language_level=3
from libcpp.string cimport string


cdef extern from "<iostream>" namespace "std" nogil:
    cdef cppclass ostream:
        pass
    cdef cppclass istream:
        pass


cdef extern from "<sstream>" namespace "std" nogil:
    cdef cppclass stringstream(istream, ostream):
        stringstream()
        string str()
        void str(const string&)
