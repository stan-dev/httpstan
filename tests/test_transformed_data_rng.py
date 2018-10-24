"""Test consistency in rng in `transformed data` block."""
import asyncio

import numpy as np

import helpers

program_code = """
    data {
        int<lower=0> N;
    }
    transformed data {
        vector[N] y;
        for (n in 1:N)
          y[n] = normal_rng(0, 1);
    }
    parameters {
        real mu;
        real<lower = 0> sigma;
    }
    model {
        y ~ normal(mu, sigma);
    }
    generated quantities {
        real mean_y = mean(y);
        real sd_y = sd(y);
    }
"""


def test_transformed_data_rng(httpstan_server):
    """Test consistency in rng in `transformed data` block."""

    host, port = httpstan_server.host, httpstan_server.port

    num_samples = num_warmup = 2000
    actions_payload = {
        "function": "stan::services::sample::hmc_nuts_diag_e",
        "num_samples": num_samples,
        "num_warmup": num_warmup,
        "random_seed": 123,
        "data": {"N": 3},
    }

    draws = asyncio.get_event_loop().run_until_complete(
        helpers.sample_then_extract(host, port, program_code, actions_payload, "mean_y")
    )
    draws1 = np.array(draws)
    # run again
    draws = asyncio.get_event_loop().run_until_complete(
        helpers.sample_then_extract(host, port, program_code, actions_payload, "mean_y")
    )
    draws2 = np.array(draws)
    assert all(np.array(draws1) < 5)
    assert all(np.array(draws2) < 5)
    assert (draws1 == draws2).all()

    # run with different seed
    actions_payload["random_seed"] = 456
    draws = asyncio.get_event_loop().run_until_complete(
        helpers.sample_then_extract(host, port, program_code, actions_payload, "mean_y")
    )
    draws3 = np.array(draws)
    assert (draws1 != draws3).all()
