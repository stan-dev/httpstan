#ifndef STAN_SERVICES_SAMPLE_STANDALONE_GQS_HPP
#define STAN_SERVICES_SAMPLE_STANDALONE_GQS_HPP

#include <stan/callbacks/interrupt.hpp>
#include <stan/callbacks/logger.hpp>
#include <stan/callbacks/writer.hpp>
#include <stan/services/error_codes.hpp>
#include <stan/services/util/create_rng.hpp>
#include <stan/services/util/gq_writer.hpp>
#include <string>
#include <vector>

namespace stan {
  namespace services {

    /**
     * Return the number of constrained parameters for the specified
     * model.
     *
     * @tparam Model type of model
     * @param[in] model model to query
     * @return number of constrained parameters for the model
     */
    template <class Model>
    int num_constrained_params(const Model& model) {
        std::vector<std::string> param_names;
        static const bool include_tparams = false;
        static const bool include_gqs = false;
        model.constrained_param_names(param_names, include_tparams,
                                      include_gqs);
        return param_names.size();
    }

    /**
     * Given a set of draws from a fitted model, generate corresponding
     * quantities of interest.  Data written to callback writer.
     * Return code indicates success or type of error.
     *
     * @tparam Model model class
     * @param[in] model instantiated model
     * @param[in] draws sequence of draws of unconstrained parameters
     * @param[in] seed seed to use for randomization
     * @param[in, out] interrupt called every iteration
     * @param[in, out] logger logger to which to write warning and error messages
     * @param[in, out] sample_writer writer to which draws are written
     * @return error code
     */
    template <class Model>
    int standalone_generate(const Model& model,
                            const std::vector<std::vector<double> >& draws,
                            unsigned int seed,
                            callbacks::interrupt& interrupt,
                            callbacks::logger& logger,
                            callbacks::writer& sample_writer) {
      if (draws.empty()) {
        logger.error("Empty set of draws from fitted model.");
        return error_codes::DATAERR;
      }

      int num_params = num_constrained_params(model);
      std::vector<std::string> gq_names;
      static const bool include_tparams = false;
      static const bool include_gqs = true;
      model.constrained_param_names(gq_names, include_tparams, include_gqs);
      if (!(static_cast<size_t>(num_params) < gq_names.size())) {
        logger.error("Model doesn't generate any quantities of interest.");
        return error_codes::CONFIG;
      }

      util::gq_writer writer(sample_writer, logger, num_params);
      boost::ecuyer1988 rng = util::create_rng(seed, 1);
      writer.write_gq_names(model);

      std::stringstream msg;
      for (const std::vector<double>& draw : draws) {
        if (static_cast<size_t>(num_params) != draw.size()) {
          msg << "Wrong number of params in draws from fitted model.  ";
          msg << "Expecting " << num_params << " columns, ";
          msg << "found " << draws[0].size() << " columns.";
          std::string msgstr = msg.str();
          logger.error(msgstr);
          return error_codes::DATAERR;
        }
        interrupt();  // call out to interrupt and fail
        writer.write_gq_values(model, rng, draw);
      }
      return error_codes::OK;
    }

  }
}
#endif
