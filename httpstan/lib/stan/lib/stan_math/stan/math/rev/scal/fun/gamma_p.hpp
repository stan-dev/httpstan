#ifndef STAN_MATH_REV_SCAL_FUN_GAMMA_P_HPP
#define STAN_MATH_REV_SCAL_FUN_GAMMA_P_HPP

#include <stan/math/rev/core.hpp>
#include <stan/math/prim/scal/fun/digamma.hpp>
#include <stan/math/prim/scal/fun/gamma_p.hpp>
#include <stan/math/prim/scal/fun/tgamma.hpp>
#include <valarray>

namespace stan {
  namespace math {

    namespace {
      class gamma_p_vv_vari : public op_vv_vari {
      public:
        gamma_p_vv_vari(vari* avi, vari* bvi) :
          op_vv_vari(gamma_p(avi->val_, bvi->val_),
                     avi, bvi) {
        }
        void chain() {
          // return zero derivative as gamma_p is flat
          // to machine precision for b / a > 10
          if (std::fabs(bvi_->val_ / avi_->val_) > 10 ) return;

          double u = gamma_p(avi_->val_, bvi_->val_);

          double S = 0.0;
          double s = 1.0;
          double l = std::log(bvi_->val_);
          double g = tgamma(avi_->val_);
          double dig = digamma(avi_->val_);

          int k = 0;
          double delta = s / (avi_->val_ * avi_->val_);

          while (std::fabs(delta) > 1e-6) {
            S += delta;
            ++k;
            s *= -bvi_->val_ / k;
            delta = s / ((k + avi_->val_) * (k + avi_->val_));
          }

          avi_->adj_ -= adj_ * ((u) * (dig - l)
                                + std::exp(avi_->val_ * l) * S / g);
          bvi_->adj_ += adj_ * (std::exp(-bvi_->val_)
                                * std::pow(bvi_->val_, avi_->val_ - 1.0) / g);
        }
      };

      class gamma_p_vd_vari : public op_vd_vari {
      public:
        gamma_p_vd_vari(vari* avi, double b) :
          op_vd_vari(gamma_p(avi->val_, b),
                     avi, b) {
        }
        void chain() {
          // return zero derivative as gamma_p is flat
          // to machine precision for b / a > 10
          if (std::fabs(bd_ / avi_->val_) > 10)
            return;

          double u = gamma_p(avi_->val_, bd_);

          double S = 0.0;
          double s = 1.0;
          double l = std::log(bd_);
          double g = tgamma(avi_->val_);
          double dig = digamma(avi_->val_);

          int k = 0;
          double delta = s / (avi_->val_ * avi_->val_);

          while (std::fabs(delta) > 1e-6) {
            S += delta;
            ++k;
            s *= -bd_ / k;
            delta = s / ((k + avi_->val_) * (k + avi_->val_));
          }

          avi_->adj_ -= adj_ * ((u) * (dig - l)
                                + std::exp(avi_->val_ * l) * S / g);
        }
      };

      class gamma_p_dv_vari : public op_dv_vari {
      public:
        gamma_p_dv_vari(double a, vari* bvi) :
          op_dv_vari(gamma_p(a, bvi->val_),
                     a, bvi) {
        }
        void chain() {
          // return zero derivative as gamma_p is flat to
          // machine precision for b / a > 10
          if (std::fabs(bvi_->val_ / ad_) > 10 )
            return;
          bvi_->adj_ += adj_
            * (std::exp(-bvi_->val_) * std::pow(bvi_->val_, ad_ - 1.0)
               / tgamma(ad_));
        }
      };
    }

    inline var gamma_p(const var& a,
                       const var& b) {
      return var(new gamma_p_vv_vari(a.vi_, b.vi_));
    }

    inline var gamma_p(const var& a,
                       double b) {
      return var(new gamma_p_vd_vari(a.vi_, b));
    }

    inline var gamma_p(double a,
                       const var& b) {
      return var(new gamma_p_dv_vari(a, b.vi_));
    }

  }
}
#endif
