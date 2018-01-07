#ifndef STAN_LANG_AST_NODE_DOUBLE_LITERAL_DEF_HPP
#define STAN_LANG_AST_NODE_DOUBLE_LITERAL_DEF_HPP

#include <stan/lang/ast.hpp>

namespace stan {
  namespace lang {

    double_literal::double_literal() : type_(double_type(), 0U) { }

    double_literal::double_literal(double val)
      : val_(val), type_(double_type(), 0U) {  }

  }
}
#endif
