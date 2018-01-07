#include <test/unit/math/mix/mat/util/autodiff_tester.hpp>

struct op_multiply_equal_f {
  template <typename T1, typename T2>
  static typename boost::math::tools::promote_args<T1, T2>::type
  apply(const T1& x1, const T2& x2) {
    typename boost::math::tools::promote_args<T1, T2>::type y = x1;
    y *= x2;
    return y;
  }
};

TEST(mathMixCore, operatorMultiplyEqual) {
  stan::math::test::test_common_args<op_multiply_equal_f, false>();
}
