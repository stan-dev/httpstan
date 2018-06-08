#ifndef STAN_LANG_AST_NODE_POSITIVE_ORDERED_VAR_DECL_DEF_HPP
#define STAN_LANG_AST_NODE_POSITIVE_ORDERED_VAR_DECL_DEF_HPP

#include <stan/lang/ast.hpp>
#include <string>
#include <vector>

namespace stan {
  namespace lang {

    positive_ordered_var_decl::positive_ordered_var_decl()
      : base_var_decl(vector_type()) { }

    positive_ordered_var_decl::positive_ordered_var_decl(const expression& K,
                                        const std::string& name,
                                        const std::vector<expression>& dims,
                                        const expression& def)

      : base_var_decl(name, dims, vector_type(), def), K_(K) { }

  }
}
#endif
