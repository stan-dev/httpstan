#include <stan/math/rev/scal.hpp>
#include <gtest/gtest.h>
#include <test/unit/math/prim/scal/fun/promote_type_test_util.hpp>

// there is no agrad-defined version of promote_scalar, so this is
// just testing that it works with non-inter-convertible types (double
// can be assigned to var, but not vice-versa)

TEST(AgradRevFunctionsPromoteScalar, Mismatch) {
  using stan::math::var;
  using stan::math::promote_scalar;
  EXPECT_FLOAT_EQ(2.3, promote_scalar<var>(2.3).val());
}
