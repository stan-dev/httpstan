#include <stan/services/error_codes.hpp>
#include <stan/services/sample/standalone_gqs.hpp>
#include <stan/callbacks/stream_writer.hpp>
#include <stan/callbacks/stream_logger.hpp>
#include <stan/io/empty_var_context.hpp>
#include <test/test-models/good/services/test_gq.hpp>
#include <test/unit/services/instrumented_callbacks.hpp>
#include <test/unit/util.hpp>
#include <gtest/gtest.h>
#include <iostream>

class ServicesStandaloneGQ : public testing::Test {
public:
  ServicesStandaloneGQ()
    : model(context, &model_log) {}

  stan::io::empty_var_context context;
  std::stringstream model_log;
  stan_model model;
  std::stringstream sample_ss, logger_ss;
  stan::test::unit::instrumented_interrupt interrupt;
};

TEST_F(ServicesStandaloneGQ, numParams) {
  // model test_gq.stan has 2 params
  int num_params = stan::services::num_constrained_params(model);
  EXPECT_EQ(num_params, 2);
}

TEST_F(ServicesStandaloneGQ, genDraws_good) {
  std::vector<double> draw1;
  draw1.push_back(-2.345);
  draw1.push_back(-6.789);
  std::vector<double> draw2;
  draw2.push_back(-3.123);
  draw2.push_back(-4.123);
  std::vector<std::vector<double> > draws;
  draws.push_back(draw1);
  draws.push_back(draw2);
  const std::vector<std::vector<double> > cdraws(draws);
  stan::callbacks::stream_writer sample_writer(sample_ss, "");
  stan::callbacks::stream_logger logger(logger_ss,
                                        logger_ss,
                                        logger_ss,
                                        logger_ss,
                                        logger_ss);
  int return_code = stan::services::standalone_generate(model,
                                                        cdraws,
                                                        12345,
                                                        interrupt,
                                                        logger,
                                                        sample_writer);
  // model test_gq.stan gen quantities block has 3 params:  xqg, y_rep.1, y_rep.2
  EXPECT_EQ(return_code, stan::services::error_codes::OK);
  EXPECT_EQ(count_matches("xgq",sample_ss.str()),1);
  EXPECT_EQ(count_matches("y_rep",sample_ss.str()),2);
  // 2 draws + 1 header = 3 lines output
  EXPECT_EQ(count_matches("\n",sample_ss.str()),3);
}

TEST_F(ServicesStandaloneGQ, genDraws_bad) {
  std::vector<double> draw1;
  draw1.push_back(-2.345);
  draw1.push_back(-6.789);
  std::vector<double> draw2;
  draw2.push_back(-3.123);
  std::vector<std::vector<double> > draws;
  draws.push_back(draw1);
  draws.push_back(draw2);
  const std::vector<std::vector<double> > cdraws(draws);
  stan::callbacks::stream_writer sample_writer(sample_ss, "");
  stan::callbacks::stream_logger logger(logger_ss,
                                        logger_ss,
                                        logger_ss,
                                        logger_ss,
                                        logger_ss);
  int return_code = stan::services::standalone_generate(model,
                                                        cdraws,
                                                        12345,
                                                        interrupt,
                                                        logger,
                                                        sample_writer);
  EXPECT_EQ(return_code, stan::services::error_codes::DATAERR);
}

TEST_F(ServicesStandaloneGQ, genDraws_empty) {
  std::vector<std::vector<double> > draws;
  const std::vector<std::vector<double> > cdraws(draws);
  stan::callbacks::stream_writer sample_writer(sample_ss, "");
  stan::callbacks::stream_logger logger(logger_ss,
                                        logger_ss,
                                        logger_ss,
                                        logger_ss,
                                        logger_ss);
  int return_code = stan::services::standalone_generate(model,
                                                        cdraws,
                                                        12345,
                                                        interrupt,
                                                        logger,
                                                        sample_writer);
  EXPECT_EQ(return_code, stan::services::error_codes::DATAERR);
  EXPECT_EQ(count_matches("Empty set of draws",logger_ss.str()),1);
}

TEST_F(ServicesStandaloneGQ, genDraws_missing_params) {
  std::vector<double> draw1;
  draw1.push_back(-2.345);
  std::vector<double> draw2;
  draw2.push_back(-3.123);
  std::vector<std::vector<double> > draws;
  draws.push_back(draw1);
  draws.push_back(draw2);
  const std::vector<std::vector<double> > cdraws(draws);
  stan::callbacks::stream_writer sample_writer(sample_ss, "");
  stan::callbacks::stream_logger logger(logger_ss,
                                        logger_ss,
                                        logger_ss,
                                        logger_ss,
                                        logger_ss);
  int return_code = stan::services::standalone_generate(model,
                                                        cdraws,
                                                        12345,
                                                        interrupt,
                                                        logger,
                                                        sample_writer);
  EXPECT_EQ(return_code, stan::services::error_codes::DATAERR);
  EXPECT_EQ(count_matches("Wrong number of params",logger_ss.str()),1);
}


TEST_F(ServicesStandaloneGQ, genDraws_too_many_params) {
  std::vector<double> draw1;
  draw1.push_back(-2.345);
  draw1.push_back(-2.345);
  draw1.push_back(-2.345);
  draw1.push_back(-2.345);
  std::vector<double> draw2;
  draw2.push_back(-3.123);
  draw1.push_back(-2.345);
  draw1.push_back(-2.345);
  draw1.push_back(-2.345);
  std::vector<std::vector<double> > draws;
  draws.push_back(draw1);
  draws.push_back(draw2);
  const std::vector<std::vector<double> > cdraws(draws);
  stan::callbacks::stream_writer sample_writer(sample_ss, "");
  stan::callbacks::stream_logger logger(logger_ss,
                                        logger_ss,
                                        logger_ss,
                                        logger_ss,
                                        logger_ss);
  int return_code = stan::services::standalone_generate(model,
                                                        cdraws,
                                                        12345,
                                                        interrupt,
                                                        logger,
                                                        sample_writer);
  EXPECT_EQ(return_code, stan::services::error_codes::DATAERR);
  EXPECT_EQ(count_matches("Wrong number of params",logger_ss.str()),1);
}
