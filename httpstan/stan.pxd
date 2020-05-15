# distutils: language=c++
# cython: language_level=3
cimport libcpp
from libcpp.string cimport string
from libcpp.vector cimport vector

# stan io

cdef extern from "stan/io/var_context.hpp" namespace "stan::io" nogil:
    cdef cppclass var_context:
        libcpp.bool contains_r(const string&)
        libcpp.bool contains_i(const string&)
        vector[double] vals_r(const string&)
        vector[size_t] dims_r(const string&)
        vector[int] vals_i(const string&)
        vector[size_t] dims_i(const string&)
        void names_r(vector[string]&)
        void names_i(vector[string]&)
        libcpp.bool remove(const string&)


cdef extern from "<stan/io/array_var_context.hpp>" namespace "stan::io" nogil:
    cdef cppclass array_var_context(var_context):
        void array_var_context(vector[string]& names_r,
                            vector[double]& values_r,
                            vector[vector[size_t]]& dim_r,
                            vector[string]& names_i,
                            vector[int]& values_i,
                            vector[vector[size_t]]& dim_i)


# stan callbacks

cdef extern from "<stan/callbacks/writer.hpp>" namespace "stan::callbacks" nogil:
    cdef cppclass writer:
        pass

cdef extern from "<stan/callbacks/stream_logger.hpp>" namespace "stan::callbacks" nogil:
    cdef cppclass logger:
        pass


cdef extern from "stan/callbacks/interrupt.hpp" namespace "stan::callbacks" nogil:
    cdef cppclass interrupt:
        void operator()()


# httpstan custom callbacks

cdef extern from "socket_writer.hpp" namespace "stan::callbacks" nogil:
    cdef cppclass socket_writer(writer):
        socket_writer(string& socket_filename)
        socket_writer(string& socket_filename, string& comment_prefix)


cdef extern from "socket_logger.hpp" namespace "stan::callbacks" nogil:
    cdef cppclass socket_logger(logger):
        socket_logger(string& socket_filename)
        socket_logger(string& socket_filename, string& comment_prefix)


# stan sample

cdef extern from "stan/services/sample/hmc_nuts_diag_e_adapt.hpp" namespace "stan::services::sample" nogil:
    # Note: if function arguments or argument names change, update schemas in httpstan.schemas
    # Note: This function can raise a C++ exception (e.g., initialization failed)
    int hmc_nuts_diag_e_adapt[Model](Model& model, var_context& init,
                                     unsigned int random_seed, unsigned int chain, double init_radius,
                                     int num_warmup, int num_samples, int num_thin, libcpp.bool save_warmup,
                                     int refresh, double stepsize, double stepsize_jitter, int max_depth,
                                     double delta, double gamma, double kappa, double t0, unsigned int init_buffer,
                                     unsigned int term_buffer, unsigned int window,
                                     interrupt& interrupt, logger& logger, writer& init_writer,
                                     writer& sample_writer, writer& diagnostic_writer) except +
