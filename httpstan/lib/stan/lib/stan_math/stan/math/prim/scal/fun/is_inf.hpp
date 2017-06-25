#ifndef STAN_MATH_PRIM_SCAL_FUN_IS_INF_HPP
#define STAN_MATH_PRIM_SCAL_FUN_IS_INF_HPP

#include <boost/math/special_functions/fpclassify.hpp>

namespace stan {
  namespace math {

    /**
     * Returns 1 if the input is infinite and 0 otherwise.
     *
     * Delegates to <code>boost::math::isinf</code>.
     *
     * @param x Value to test.
     * @return <code>1</code> if the value is infinite.
     */
    inline int
    is_inf(double x) {
      return boost::math::isinf(x);
    }

  }
}

#endif
