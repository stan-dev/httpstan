#ifndef STAN_MATH_PRIM_ARR_FUN_DOT_SELF_HPP
#define STAN_MATH_PRIM_ARR_FUN_DOT_SELF_HPP

#include <vector>
#include <cstddef>

namespace stan {
  namespace math {

    inline double dot_self(const std::vector<double>& x) {
      double sum = 0.0;
      for (size_t i = 0; i < x.size(); ++i)
        sum += x[i] * x[i];
      return sum;
    }

  }
}
#endif
