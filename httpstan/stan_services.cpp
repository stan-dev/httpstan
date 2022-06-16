#include <algorithm>
#include <exception>
#include <math.h>
#include <ostream>
#include <string>

#include <stan/callbacks/interrupt.hpp>
#include <stan/callbacks/stream_logger.hpp>
#include <stan/callbacks/writer.hpp>
#include <stan/io/array_var_context.hpp>
#include <stan/io/var_context.hpp>
#include <stan/model/model_base.hpp>
#include <stan/services/sample/fixed_param.hpp>
#include <stan/services/sample/hmc_nuts_diag_e_adapt.hpp>

#include <stan/math/rev/core/autodiffstackstorage.hpp>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>

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
std::vector<std::string> get_param_names(py::dict data) {
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
std::vector<std::vector<size_t>> get_dims(py::dict data) {
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
double log_prob(py::dict data, const std::vector<double> &unconstrained_parameters, bool adjust_transform) {
  double lp;
  stan::io::array_var_context &var_context = new_array_var_context(data);
  // random_seed, the second argument, is unused but the function requires it.
  stan::model::model_base &model = new_model(var_context, (unsigned int)1, &std::cout);
  if (unconstrained_parameters.size() != model.num_params_r()) {
    throw std::runtime_error(
        "The number of parameters does not match the number of unconstrained parameters in the model.");
  }
  std::vector<stan::math::var> ad_params_r;
  ad_params_r.reserve(model.num_params_r());
  for (size_t i = 0; i < model.num_params_r(); i++) {
    ad_params_r.push_back(unconstrained_parameters[i]);
  }
  // calculate logprob
  std::vector<int> params_i(model.num_params_i(), 0);
  std::exception_ptr p;
  try {
    // params_i, the second argument, is unused but the function requires it (see model_base.hpp).
    if (adjust_transform) {
      lp = model.template log_prob<true, true>(ad_params_r, params_i, &std::cout).val();
    } else {
      lp = model.template log_prob<true, false>(ad_params_r, params_i, &std::cout).val();
    }
    stan::math::recover_memory();
  } catch (std::exception &ex) {
    stan::math::recover_memory();
    p = std::current_exception();
  }

  delete &model;
  delete &var_context;

  if (p)
    std::rethrow_exception(p);

  return lp;
}


struct StanLogpFunctionCtx {
  py::dict data;
  stan::io::var_context *var_context;
  stan::model::model_base *model;
};

extern "C" {
  int logp_gradient(size_t ndim, const double *unconstrained_parameters, double *gradient, double *logp, void *ctx) {
    try {
      const auto func = reinterpret_cast<const struct StanLogpFunctionCtx*>(ctx);

      size_t num_params = func->model->num_params_r();

      // Unfortunately this copies the data. But I think stan only accepts data that is owned by a vector.
      std::vector<double> params_r = std::vector<double>(unconstrained_parameters, unconstrained_parameters + num_params);
      std::vector<double> gradient_vector = std::vector<double>(num_params);
      std::vector<int> params_i(func->model->num_params_i(), 0);

      int returncode = 0;
      try {
        // params_i, the third argument, is unused but the function requires it (see model_base.hpp).
        *logp = stan::model::log_prob_grad<true, true>(*func->model, params_r, params_i, gradient_vector, &std::cout);
        std::copy(gradient_vector.begin(), gradient_vector.end(), gradient);
      } catch (std::exception &ex) {
        returncode = 1;
      }

      if (!isfinite(*logp)) {
        returncode = 2;
      }

      auto has_nan = std::any_of(
        gradient_vector.begin(),
        gradient_vector.end(),
        [](double const& val) { return !isfinite(val); }
      );

      if (has_nan) {
        returncode = 3;
      }

      return returncode;
    } catch (std::exception &ex) {
      return -1;
    }
  }
}

std::uintptr_t new_logp_ctx(py::dict data) {
  stan::io::array_var_context &var_context = new_array_var_context(data);
  stan::model::model_base &model = new_model(var_context, (unsigned int)1, &std::cout);

  stan::math::ChainableStack::instance_ = new stan::math::AutodiffStackSingleton<stan::math::vari_base, stan::math::chainable_alloc>::AutodiffStackStorage();

  auto ctx = new StanLogpFunctionCtx {
    data,
    &var_context,
    &model,
  };

  return reinterpret_cast<std::uintptr_t>(ctx);
}

void free_logp_ctx(std::uintptr_t ctx) {
  auto func = reinterpret_cast<struct StanLogpFunctionCtx*>(ctx);
  delete func->model;
  delete func->var_context;
  delete func;
}

std::uintptr_t logp_func(std::uintptr_t ctx) {
  return reinterpret_cast<std::uintptr_t>(&logp_gradient);
}

size_t num_unconstrained_parameters(std::uintptr_t ctx) {
  auto func = reinterpret_cast<struct StanLogpFunctionCtx*>(ctx);
  return func->model->num_params_r();
}

py::array_t<double> write_array_ctx(std::uintptr_t ctx, const py::array_t<double> unconstrained_parameters,
                                bool include_tparams = true, bool include_gqs = true, int seed = 0) {
  auto func = reinterpret_cast<struct StanLogpFunctionCtx*>(ctx);
  boost::ecuyer1988 base_rng(seed);
  std::vector<double> params_r_constrained_vec;
  if (unconstrained_parameters.size() != func->model->num_params_r()) {
    throw std::runtime_error(
        "The number of parameters does not match the number of unconstrained parameters in the model.");
  }

  if (unconstrained_parameters.ndim() != 1) {
    throw std::runtime_error(
      "Array of unconstrained parameters must be one dimensional"
    );
  }

  // The params_r parameter is incorrectly declared as non-const in Stan C++.
  // Unconstrained_parameters are cast from const to non-const below, as required by Stan (see model_base.hpp).
  std::vector<double> params_r = std::vector<double>(unconstrained_parameters.data(), unconstrained_parameters.data() + unconstrained_parameters.size());
  // constrain parameters to their defined support
  std::exception_ptr p;
  std::vector<int> params_i(func->model->num_params_i(), 0);
  try {
    // params_i, the third argument, is unused but the function requires it (see model_base.hpp).
    func->model->write_array(base_rng, params_r, params_i, params_r_constrained_vec, include_tparams, include_gqs, &std::cout);
  } catch (std::exception &ex) {
    p = std::current_exception();
  }

  if (p)
    std::rethrow_exception(p);

  auto params_r_constrained = py::array_t<double>(params_r_constrained_vec.size());
  double *ptr = static_cast<double *>(params_r_constrained.request().ptr);

  for (size_t idx = 0; idx < params_r_constrained_vec.size(); idx++) {
    ptr[idx] = params_r_constrained_vec[idx];
  }

  return params_r_constrained;
}

// See exported docstring
std::vector<double> log_prob_grad(py::dict data, const std::vector<double> &unconstrained_parameters,
                                  bool adjust_transform) {
  std::vector<double> gradient;
  stan::io::array_var_context &var_context = new_array_var_context(data);
  // random_seed, the second argument, is unused but the function requires it.
  stan::model::model_base &model = new_model(var_context, (unsigned int)1, &std::cout);
  if (unconstrained_parameters.size() != model.num_params_r()) {
    throw std::runtime_error(
        "The number of parameters does not match the number of unconstrained parameters in the model.");
  }
  // The params_r parameter is incorrectly declared as non-const in Stan C++.
  // Unconstrained_parameters are cast from const to non-const below, as required by Stan (see model_base.hpp).
  std::vector<double> &params_r = const_cast<std::vector<double> &>(unconstrained_parameters);
  // calculate gradient
  std::exception_ptr p;
  std::vector<int> params_i(model.num_params_i(), 0);
  try {
    // params_i, the third argument, is unused but the function requires it (see model_base.hpp).
    if (adjust_transform) {
      stan::model::log_prob_grad<true, true>(model, params_r, params_i, gradient, &std::cout);
    } else {
      stan::model::log_prob_grad<true, false>(model, params_r, params_i, gradient, &std::cout);
    }
  } catch (std::exception &ex) {
    p = std::current_exception();
  }

  delete &model;
  delete &var_context;

  if (p)
    std::rethrow_exception(p);

  return gradient;
}

// See exported docstring
std::vector<double> write_array(py::dict data, const std::vector<double> &unconstrained_parameters,
                                bool include_tparams = true, bool include_gqs = true) {
  boost::ecuyer1988 base_rng(0);
  std::vector<double> params_r_constrained;
  stan::io::array_var_context &var_context = new_array_var_context(data);
  // random_seed, the second argument, is unused but the function requires it.
  stan::model::model_base &model = new_model(var_context, (unsigned int)1, &std::cout);
  if (unconstrained_parameters.size() != model.num_params_r()) {
    throw std::runtime_error(
        "The number of parameters does not match the number of unconstrained parameters in the model.");
  }
  // The params_r parameter is incorrectly declared as non-const in Stan C++.
  // Unconstrained_parameters are cast from const to non-const below, as required by Stan (see model_base.hpp).
  std::vector<double> &params_r = const_cast<std::vector<double> &>(unconstrained_parameters);
  // constrain parameters to their defined support
  std::exception_ptr p;
  std::vector<int> params_i(model.num_params_i(), 0);
  try {
    // params_i, the third argument, is unused but the function requires it (see model_base.hpp).
    model.write_array(base_rng, params_r, params_i, params_r_constrained, include_tparams, include_gqs, &std::cout);
  } catch (std::exception &ex) {
    p = std::current_exception();
  }

  delete &model;
  delete &var_context;

  if (p)
    std::rethrow_exception(p);

  return params_r_constrained;
}

// See exported docstring
std::vector<double> transform_inits(py::dict data, py::dict constrained_parameters) {
  std::vector<double> params_r_unconstrained;
  stan::io::array_var_context &var_context = new_array_var_context(data);
  // random_seed, the second argument, is unused but the function requires it.
  stan::model::model_base &model = new_model(var_context, (unsigned int)1, &std::cout);
  stan::io::var_context &param_var_context = new_array_var_context(constrained_parameters);
  // unconstrain parameters from their defined support
  std::exception_ptr p;
  std::vector<int> params_i(model.num_params_i(), 0);
  try {
    // params_i, the second argument, is unused but the function requires it (see model_base.hpp).
    model.transform_inits(param_var_context, params_i, params_r_unconstrained, &std::cout);
  } catch (std::exception &ex) {
    p = std::current_exception();
  }

  delete &model;
  delete &var_context;
  delete &param_var_context;

  if (p)
    std::rethrow_exception(p);

  return params_r_unconstrained;
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

// See exported docstring
int fixed_param_wrapper(std::string socket_filename, py::dict data, py::dict init, int random_seed, int chain,
                        double init_radius, int num_samples, int num_thin, int refresh) {
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
    return_code = stan::services::sample::fixed_param(model, init_var_context, random_seed, chain, init_radius,
                                                      num_samples, num_thin, refresh, interrupt, *logger, *init_writer,
                                                      *sample_writer, *diagnostic_writer);
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
  m.def("get_param_names", &get_param_names, py::arg("data"), "Call the ``get_param_names`` method of the model.");
  m.def("constrained_param_names", &constrained_param_names, py::arg("data"),
        "Call the ``constrained_param_names`` method of the model.");
  m.def("get_dims", &get_dims, py::arg("data"), "Call the ``get_dims`` method of the model.");
  m.def("log_prob", &log_prob, py::arg("data"), py::arg("unconstrained_parameters"), py::arg("adjust_transform"),
        "Call the ``log_prob`` method of the model.");
  m.def("log_prob_grad", &log_prob_grad, py::arg("data"), py::arg("unconstrained_parameters"),
        py::arg("adjust_transform"), "Call stan::model::log_prob_grad");
  m.def("write_array", &write_array, py::arg("data"), py::arg("unconstrained_parameters"), py::arg("include_tparams"),
        py::arg("include_gqs"), "Call the ``write_array`` method of the model.");
  m.def("transform_inits", &transform_inits, py::arg("data"), py::arg("constrained_parameters"),
        "Call the ``transform_inits`` method of the model.");
  m.def("hmc_nuts_diag_e_adapt_wrapper", &hmc_nuts_diag_e_adapt_wrapper, py::arg("socket_filename"), py::arg("data"),
        py::arg("init"), py::arg("random_seed"), py::arg("chain"), py::arg("init_radius"), py::arg("num_warmup"),
        py::arg("num_samples"), py::arg("num_thin"), py::arg("save_warmup"), py::arg("refresh"), py::arg("stepsize"),
        py::arg("stepsize_jitter"), py::arg("max_depth"), py::arg("delta"), py::arg("gamma"), py::arg("kappa"),
        py::arg("t0"), py::arg("init_buffer"), py::arg("term_buffer"), py::arg("window"),
        "Call stan::services::sample::hmc_nuts_diag_e_adapt");
  m.def("fixed_param_wrapper", &fixed_param_wrapper, py::arg("socket_filename"), py::arg("data"), py::arg("init"),
        py::arg("random_seed"), py::arg("chain"), py::arg("init_radius"), py::arg("num_samples"), py::arg("num_thin"),
        py::arg("refresh"), "Call stan::services::sample::fixed_param");
  m.def("new_logp_ctx", &new_logp_ctx, py::arg("data"), "Create new logp function context");
  m.def("free_logp_ctx", &free_logp_ctx, py::arg("ctx"), "Destroy a logp function context");
  m.def("logp_func", &logp_func, py::arg("ctx"), "Return a C-function for computing logp values and gradients.");
  m.def("num_unconstrained_parameters", &num_unconstrained_parameters, py::arg("ctx"), "Get the number of unconstrained parameters");
  m.def("write_array_ctx", &write_array_ctx, py::arg("ctx"), py::arg("unconstrained_parameters"), py::arg("include_tparams"),
        py::arg("include_gqs"), py::arg("seed"), "Save all parameters at unconstrained parameter position.");
}
