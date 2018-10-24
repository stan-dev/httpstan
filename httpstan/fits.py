"""Helper functions for Stan fits."""
import hashlib
import pickle
import random
import sys

import httpstan
import httpstan.stan


def calculate_fit_name(function: str, model_name: str, data: dict, kwargs: dict) -> str:
    """Calculate fit name from parameters and data.

    If a random seed is provided, a fit is a deterministic function of
    the model, data, and parameters. If no random seed is provided,
    this function returns a random string.

    If a random seed is provided, a fit id is a hash of the concatenation of
    binary representations of the arguments to ``services_stub.call``
    (type, model, data, kwargs):

    -   UTF-8 encoded name of service function (e.g., ``hmc_nuts_diag_e_adapt``)
    -   UTF-8 encoded Stan model name (which is derived from a hash of ``program_code``)
    -   Bytes of pickled data dictionary
    -   Bytes of pickled kwargs dictionary
    -   UTF-8 encoded version of Stan
    -   UTF-8 encoded version of `httpstan`
    -   UTF-8 encoded name of OS (for good measure)

    Arguments:
        function: name of service function
        model_name: Stan model name
        data: data dictionary passed to service function
        kwargs: kwargs passed to service function

    Returns:
        str: fit name

    """
    # digest_size of 5 means we expect a collision after a million fits
    digest_size = 5
    if "random_seed" not in kwargs:
        random_bytes = random.getrandbits(digest_size * 8).to_bytes(digest_size, sys.byteorder)
        return f"{model_name}/fits/{random_bytes.hex()}"
    hash = hashlib.blake2b(digest_size=digest_size)
    hash.update(function.encode())
    hash.update(model_name.encode())
    hash.update(pickle.dumps(data))
    hash.update(pickle.dumps(kwargs))
    hash.update(httpstan.stan.version().encode())
    hash.update(httpstan.__version__.encode())
    hash.update(sys.platform.encode())
    return f"{model_name}/fits/{hash.hexdigest()}"
