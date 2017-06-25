#ifndef TEST_UNIT_MATH_ODE_HARMONIC_OSCILLATOR
#define TEST_UNIT_MATH_ODE_HARMONIC_OSCILLATOR

#include <stan/math/prim/scal.hpp>
#include <stdexcept>

struct harm_osc_ode_fun {
  template <typename T0, typename T1, typename T2>
  inline
  std::vector<typename stan::return_type<T1,T2>::type>
  operator()(const T0& t_in, // initial time
             const std::vector<T1>& y_in, //initial positions
             const std::vector<T2>& theta, // parameters
             const std::vector<double>& x, // double data
             const std::vector<int>& x_int,
             std::ostream* msgs) const { // integer data
    if (y_in.size() != 2)
      throw std::domain_error("this function was called with inconsistent state");

    std::vector<typename stan::return_type<T1,T2>::type> res;
    res.push_back(y_in.at(1));
    res.push_back(-y_in.at(0) - theta.at(0)*y_in.at(1));

    return res;
  }
};

struct harm_osc_ode_data_fun {
  template <typename T0, typename T1, typename T2>
  inline
  std::vector<typename stan::return_type<T1,T2>::type>
  operator()(const T0& t_in, // initial time
             const std::vector<T1>& y_in, //initial positions
             const std::vector<T2>& theta, // parameters
             const std::vector<double>& x, // double data
             const std::vector<int>& x_int,
             std::ostream* msgs) const { // integer data
    if (y_in.size() != 2)
      throw std::domain_error("this function was called with inconsistent state");

    std::vector<typename stan::return_type<T1,T2>::type> res;
    res.push_back(x.at(0) * y_in.at(1) + x_int.at(0));
    res.push_back(-x.at(1) * y_in.at(0) - x.at(2) * theta.at(0) * y_in.at(1) + x_int.at(1));

    return res;
  }
};


struct harm_osc_ode_wrong_size_1_fun {
  template <typename T0, typename T1, typename T2>
  inline
  std::vector<typename stan::return_type<T1,T2>::type>
  operator()(const T0& t_in, // initial time
             const std::vector<T1>& y_in, //initial positions
             const std::vector<T2>& theta, // parameters
             const std::vector<double>& x, // double data
             const std::vector<int>& x_int,
             std::ostream* msgs) const { // integer data
    if (y_in.size() != 2)
      throw std::domain_error("this function was called with inconsistent state");

    std::vector<typename stan::return_type<T1,T2>::type> res;
    res.push_back(y_in.at(1));
    res.push_back(-y_in.at(0) - theta.at(0)*y_in.at(1));
    res.push_back(0);

    return res;
  }
};

struct harm_osc_ode_wrong_size_2_fun {
  template <typename T0, typename T1, typename T2>
  inline
  std::vector<typename stan::return_type<T1,T2>::type>
  operator()(const T0& t_in, // initial time
             const std::vector<T1>& y_in, //initial positions
             const std::vector<T2>& theta, // parameters
             const std::vector<double>& x, // double data
             const std::vector<int>& x_int,
             std::ostream* msgs) const { // integer data
    if (y_in.size() != 2)
      throw std::domain_error("this function was called with inconsistent state");

    std::vector<typename stan::return_type<T1,T2>::type> res;
    res.push_back(0);

    return res;
  }
};


#endif
