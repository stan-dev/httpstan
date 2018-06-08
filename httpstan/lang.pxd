# distutils: language=c++
# cython: language_level=3
cimport libcpp
from libcpp.string cimport string

from httpstan.libcpp cimport istream
from httpstan.libcpp cimport ostream


# stan lang

cdef extern from '<stan/lang/compiler.hpp>' namespace 'stan::lang' nogil:
    libcpp.bool compile(ostream * msgs,
                        istream& stan_lang_in,
                        ostream& cpp_out,
                        string& model_name) except +
