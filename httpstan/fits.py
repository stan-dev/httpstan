"""Helper functions for Stan fits."""
import base64
import hashlib
import pickle
import random
import sys

import httpstan


def calculate_fit_name(function: str, model_name: str, kwargs: dict) -> str:
    """Calculate fit name from parameters and data.

    If a random seed is provided, a fit is a deterministic function of
    the model, data, and parameters. If no random seed is provided,
    this function returns a random string.

    If a random seed is provided, a fit id is a hash of the concatenation of
    binary representations of the arguments to ``services_stub.call``
    (type, model, kwargs):

    - UTF-8 encoded name of service function (e.g., ``hmc_nuts_diag_e_adapt``)
    - UTF-8 encoded Stan model name (which is derived from a hash of ``program_code``)
    - Bytes of pickled kwargs dictionary
    - UTF-8 encoded string recording the httpstan version
    - UTF-8 encoded string identifying the system platform
    - UTF-8 encoded string identifying the system bit architecture
    - UTF-8 encoded string identifying the Python version
    - UTF-8 encoded string identifying the Python executable

    Arguments:
        function: name of service function
        model_name: Stan model name
        kwargs: kwargs passed to service function

    Returns:
        str: fit name

    """
    # digest_size of 5 means we expect a collision after a million fits
    digest_size = 5

    # cannot cache fit if no random seed provided
    if "random_seed" not in kwargs:
        random_bytes = random.getrandbits(digest_size * 8).to_bytes(digest_size, sys.byteorder)
        id = base64.b32encode(random_bytes).decode().lower()
        return f"{model_name}/fits/{id}"

    hash = hashlib.blake2b(digest_size=digest_size)
    hash.update(function.encode())
    hash.update(model_name.encode())
    hash.update(pickle.dumps(kwargs))

    # system identifiers
    hash.update(httpstan.__version__.encode())
    hash.update(sys.platform.encode())
    hash.update(str(sys.maxsize).encode())
    hash.update(sys.version.encode())
    # include sys.executable in hash to account for different `venv`s
    hash.update(sys.executable.encode())

    id = base64.b32encode(hash.digest()).decode().lower()
    return f"{model_name}/fits/{id}"
