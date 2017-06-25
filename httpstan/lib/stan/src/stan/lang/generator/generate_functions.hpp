#ifndef STAN_LANG_GENERATOR_GENERATE_FUNCTIONS_HPP
#define STAN_LANG_GENERATOR_GENERATE_FUNCTIONS_HPP

#include <stan/lang/ast.hpp>
#include <stan/lang/generator/generate_function.hpp>
#include <stan/lang/generator/generate_function_functor.hpp>
#include <ostream>
#include <vector>

namespace stan {
  namespace lang {

    /**
     * Generate function forward declarations, definitions, and
     * functors for the the specified sequence of function
     * declarations and definitions, writing to the specified stream.
     *
     * @param[in] funs sequence of function declarations and
     * definitions
     * @param[in,out] o stream for generating
     * @param[in] rcpp_export if true, comments to enable export for RCpp
     * are generated
     */
    void generate_functions(const std::vector<function_decl_def>& funs,
                            std::ostream& o, bool rcpp_export = false) {
      for (size_t i = 0; i < funs.size(); ++i) {
        generate_function(funs[i], o, rcpp_export);
        generate_function_functor(funs[i], o);
      }
    }

  }
}
#endif
