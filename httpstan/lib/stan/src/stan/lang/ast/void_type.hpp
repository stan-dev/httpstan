#ifndef STAN_LANG_AST_VOID_TYPE_HPP
#define STAN_LANG_AST_VOID_TYPE_HPP

namespace stan {
  namespace lang {

    /**
     * Void base expression type.
     */
    struct void_type {
      static const int ORDER_ID = 1;
    };

  }
}
#endif
