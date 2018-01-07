#include <test/unit/math/mix/mat/util/autodiff_tester.hpp>

struct op_minus_minus_pre_f {
  template <typename T1, typename T2>
  static typename boost::math::tools::promote_args<T1, T2>::type
  apply(const T1& x1, const T2& x2) {
    typename boost::math::tools::promote_args<T1, T2>::type y = x1;
    return --y;
  }
};

struct op_minus_minus_post_f {
  template <typename T1, typename T2>
  static typename boost::math::tools::promote_args<T1, T2>::type
  apply(const T1& x1, const T2& x2) {
    typename boost::math::tools::promote_args<T1, T2>::type y = x1;
    return y--;
  }
};

TEST(mathMixCore, operatorMinusMinusPre) {
  stan::math::test::test_common_args<op_minus_minus_pre_f, false>();
}
TEST(mathMixCore, operatorMinusMinusPost) {
  stan::math::test::test_common_args<op_minus_minus_post_f, false>();
}
