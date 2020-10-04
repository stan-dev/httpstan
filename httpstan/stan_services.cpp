#include <exception>
#include <ostream>
#include <string>

#include <stan/callbacks/interrupt.hpp>
#include <stan/callbacks/stream_logger.hpp>
#include <stan/callbacks/writer.hpp>
#include <stan/io/array_var_context.hpp>
#include <stan/model/model_base.hpp>
#include <stan/services/sample/hmc_nuts_diag_e_adapt.hpp>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "socket_logger.hpp"
#include "socket_writer.hpp"

namespace py = pybind11;

// forward declaration for function defined in another translation unit
stan::model::model_base &new_model(stan::io::var_context &data_context, unsigned int seed, std::ostream *msg_stream);

// Returns a reference variable to a new array_var_context
//
// See the C++ documentation for ``array_var_context`` for details about the
// C++ class.
// Caller takes responsibility for deleting.
stan::io::array_var_context &new_array_var_context(py::dict data) {
  py::module utils = py::module::import("httpstan.utils");
  py::tuple split_results = utils.attr("_split_data")(data);

  std::vector<std::string> names_r;
  for (auto item : split_results[0])
    names_r.push_back(item.cast<std::string>());

  std::vector<double> values_r;
  for (auto item : split_results[1])
    values_r.push_back(item.cast<double>());

  std::vector<std::vector<size_t>> dim_r;
  for (auto lst : split_results[2]) {
    std::vector<size_t> dim;
    for (auto item : lst)
      dim.push_back(item.cast<size_t>());
    dim_r.push_back(dim);
  }

  std::vector<std::string> names_i;
  for (auto item : split_results[3])
    names_i.push_back(item.cast<std::string>());

  std::vector<int> values_i;
  for (auto item : split_results[4])
    values_i.push_back(item.cast<int>());

  std::vector<std::vector<size_t>> dim_i;
  for (auto lst : split_results[5]) {
    std::vector<size_t> dim;
    for (auto item : lst)
      dim.push_back(item.cast<size_t>());
    dim_i.push_back(dim);
  }

  stan::io::array_var_context *var_context_ptr =
      new stan::io::array_var_context(names_r, values_r, dim_r, names_i, values_i, dim_i);
  return *var_context_ptr;
}

// See exported docstring
std::string model_name() {
  stan::io::array_var_context &var_context = new_array_var_context(py::dict()); // empty var_context
  // random_seed, the second argument, is unused but the function requires it.
  stan::model::model_base &model = new_model(var_context, (unsigned int)1, &std::cout);
  std::string name = model.model_name();

  delete &model;
  delete &var_context;

  return name;
}

// See exported docstring
std::vector<std::string> param_names(py::dict data) {
  std::vector<std::string> names;
  stan::io::array_var_context &var_context = new_array_var_context(data);
  // random_seed, the second argument, is unused but the function requires it.
  stan::model::model_base &model = new_model(var_context, (unsigned int)1, &std::cout);
  model.get_param_names(names);

  delete &model;
  delete &var_context;

  return names;
}

// See exported docstring
std::vector<std::string> constrained_param_names(py::dict data) {
  stan::io::array_var_context &var_context = new_array_var_context(data);
  std::vector<std::string> names;
  // random_seed, the second argument, is unused but the function requires it.
  stan::model::model_base &model = new_model(var_context, (unsigned int)1, &std::cout);
  model.constrained_param_names(names);

  delete &model;
  delete &var_context;

  return names;
}

// See exported docstring
std::vector<std::vector<size_t>> dims(py::dict data) {
  stan::io::array_var_context &var_context = new_array_var_context(data);
  std::vector<std::vector<size_t>> dims_;
  // random_seed, the second argument, is unused but the function requires it.
  stan::model::model_base &model = new_model(var_context, (unsigned int)1, &std::cout);
  model.get_dims(dims_);

  delete &model;
  delete &var_context;

  return dims_;
}

// See exported docstring
int hmc_nuts_diag_e_adapt_wrapper(std::string socket_filename, py::dict data, py::dict init, int random_seed,
                                  int chain, double init_radius, int num_warmup, int num_samples, int num_thin,
                                  bool save_warmup, int refresh, double stepsize, double stepsize_jitter,
                                  int max_depth, double delta, double gamma, double kappa, double t0, int init_buffer,
                                  int term_buffer, int window) {
  int return_code;
  stan::io::array_var_context &var_context = new_array_var_context(data);
  stan::model::model_base &model = new_model(var_context, (unsigned int)random_seed, &std::cout);
  stan::io::array_var_context &init_var_context = new_array_var_context(init);
  stan::callbacks::interrupt interrupt;
  stan::callbacks::logger *logger = new stan::callbacks::socket_logger(socket_filename, "logger:");
  stan::callbacks::writer *init_writer = new stan::callbacks::socket_writer(socket_filename, "init_writer:");
  stan::callbacks::writer *sample_writer = new stan::callbacks::socket_writer(socket_filename, "sample_writer:");
  stan::callbacks::writer *diagnostic_writer =
      new stan::callbacks::socket_writer(socket_filename, "diagnostic_writer:");
  std::exception_ptr p;
  py::gil_scoped_release release;
  try {
    return_code = stan::services::sample::hmc_nuts_diag_e_adapt(
        model, init_var_context, random_seed, chain, init_radius, num_warmup, num_samples, num_thin, save_warmup,
        refresh, stepsize, stepsize_jitter, max_depth, delta, gamma, kappa, t0, init_buffer, term_buffer, window,
        interrupt, *logger, *init_writer, *sample_writer, *diagnostic_writer);
  } catch (const std::exception &e) {
    p = std::current_exception();
  }

  delete &model;
  delete &init_var_context;
  delete logger;
  delete init_writer;
  delete sample_writer;
  delete diagnostic_writer;
  delete &var_context;

  if (p)
    std::rethrow_exception(p);

  return return_code;
}

PYBIND11_MODULE(stan_services, m) {
  m.doc() = R"pbdoc(
        Wrapped functions defined in the `stan::services` namespace.

        This Python extension module allows users to call C++ functions
        defined by the Stan library from Python.

        This module also allows calling methods of the instance of
        `stan::model::model_base` returned by the `new_model` C++ function.
    )pbdoc";
  m.def("model_name", &model_name, "Call the ``model_name`` method of the model.");
  m.def("param_names", &param_names, py::arg("data"), "Call the ``get_param_names`` method of the model.");
  m.def("constrained_param_names", &constrained_param_names, py::arg("data"),
        "Call the ``constrained_param_names`` method of the model.");
  m.def("dims", &dims, py::arg("data"), "Call the ``get_dims`` method of the model.");
  m.def("hmc_nuts_diag_e_adapt_wrapper", &hmc_nuts_diag_e_adapt_wrapper, py::arg("socket_filename"), py::arg("data"),
        py::arg("init"), py::arg("random_seed"), py::arg("chain"), py::arg("init_radius"), py::arg("num_warmup"),
        py::arg("num_samples"), py::arg("num_thin"), py::arg("save_warmup"), py::arg("refresh"), py::arg("stepsize"),
        py::arg("stepsize_jitter"), py::arg("max_depth"), py::arg("delta"), py::arg("gamma"), py::arg("kappa"),
        py::arg("t0"), py::arg("init_buffer"), py::arg("term_buffer"), py::arg("window"),
        "Call stan::services::sample::hmc_nuts_diag_e_adapt");
}
