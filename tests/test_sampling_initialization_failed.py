"""Test sampling from a model where initialization will fail.

Sampling from this model should generate ``Rejecting initial value`` logger
messages followed by a C++ exception (which Cython turns into a Python
exception). The exception is associated with the message ``Initialization
failed.``
"""
import aiohttp
import pytest

import helpers

program_code = """
parameters {
  real y;
}
model {
  y ~ uniform(100, 101);
}
"""


@pytest.mark.asyncio
async def test_sampling_initialization_failed(api_url: str) -> None:
    """Test sampling from a model where initialization will fail."""
    payload = {"function": "stan::services::sample::hmc_nuts_diag_e_adapt", "random_seed": 1}
    operation = await helpers.sample(api_url, program_code, payload)

    # verify an error occurred
    assert operation["result"]["code"] == 400
    assert "Initialization failed." in operation["result"]["message"]

    # recover the error messages sent to `logger`
    # note that the fit name is retrieved from metadata. If sampling had
    # completed without error, it would be available under `result`.
    fit_name = operation["metadata"]["fit"]["name"]

    # verify operation finished and that fit is available
    async with aiohttp.ClientSession() as session:
        fit_url = f"{api_url}/{fit_name}"
        async with session.get(fit_url) as resp:
            assert resp.status == 200

    # verify (error) messages are available
    fit_bytes_ = await helpers.fit_bytes(api_url, fit_name)
    assert isinstance(fit_bytes_, bytes)
    messages = helpers.decode_messages(fit_bytes_)

    assert len(messages) > 100

    # first message should be an "Rejecting initial value" message.
    error_message = messages[0].feature[0].string_list.value[0]
    assert "Rejecting initial value" in error_message
