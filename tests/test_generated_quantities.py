"""Superficial test of `generated quantities` block."""
import numpy as np
import pytest

import helpers

program_code = """
    parameters {
      real y;
    }
    model {
      y ~ normal(0, 1);
    }
    generated quantities {
        real y_new = y + 3;
    }
"""


@pytest.mark.asyncio
async def test_generated_quantities_block(api_url: str) -> None:
    """Test `generated_quantities` block."""
    payload = {"function": "stan::services::sample::hmc_nuts_diag_e_adapt"}
    y = np.array(await helpers.sample_then_extract(api_url, program_code, payload, "y"))
    y_new = np.array(await helpers.sample_then_extract(api_url, program_code, payload, "y_new"))
    np.testing.assert_allclose(y + 3, y_new, atol=0.001)
