#ifndef STAN_LANG_AST_NODE_COV_MATRIX_VAR_DECL_DEF_HPP
#define STAN_LANG_AST_NODE_COV_MATRIX_VAR_DECL_DEF_HPP

#include <stan/lang/ast.hpp>
#include <string>
#include <vector>

namespace stan {
  namespace lang {

    cov_matrix_var_decl::cov_matrix_var_decl()
      : base_var_decl(matrix_type()) {  }

    cov_matrix_var_decl::cov_matrix_var_decl(const expression& K,
                                         const std::string& name,
                                         const std::vector<expression>& dims,
                                         const expression& def)
      : base_var_decl(name, dims, matrix_type(), def), K_(K) { }

  }
}
#endif
