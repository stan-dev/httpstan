"""Lookup arguments and argument default values for stan::services functions."""
import enum
import functools
import inspect
import json
import time
import typing

import pkg_resources


Method = enum.Enum("Method", "SAMPLE OPTIMIZE VARIATIONAL DIAGNOSE")
DEFAULTS_LOOKUP = None  # lazy loaded by lookup_default


def _pythonize_cmdstan_type(type_name: str):
    """Turn CmdStan C++ type name into Python type.

    For example, "double" becomes `float` (the type).

    """
    if type_name == "double":
        return float
    if type_name in {"int", "unsigned int"}:
        return int
    if type_name.startswith("bool"):
        return bool
    if type_name == "list element":
        raise NotImplementedError(f"Cannot convert CmdStan `{type_name}` to Python type.")
    if type_name == "string":
        return str
    raise ValueError(f"Cannot convert CmdStan `{type_name}` to Python type.")


@functools.lru_cache()
def lookup_default(method: Method, arg: str) -> typing.Union[float, int]:
    """Fetch default for named argument in a stan:services `function`.

    Uses defaults from CmdStan. The file ``cmdstan-help-all.json`` is generated
    with the script ``scripts/parse_cmdstan_help.py`` from the output of running
    a CmdStan binary with the argument ``help-all`` (e.g., ``
    examples/bernoulli/bernoulli help-all``)

    """
    global DEFAULTS_LOOKUP
    if DEFAULTS_LOOKUP is None:
        DEFAULTS_LOOKUP = json.loads(
            pkg_resources.resource_string(__name__, "cmdstan-help-all.json").decode()
        )
    # special handling for random_seed, argument name differs from CmdStan name
    if arg == "random_seed":
        # CmdStan generates an unsigned integer using boost::posix_time (line 80 of command.hpp)
        return int(time.time())
    # special handling for chain, argument name differs from CmdStan name
    if arg == "chain":
        return 1
    # special handling for ``num_thin``, since argument name differs from CmdStan name
    if arg == "num_thin":
        arg = "thin"
    # special handling for ``refresh`` since the choice is up to httpstan, value
    # determines how often messages are sent to callback logger
    if arg == "refresh":
        return 100
    # special handling for init_radius. There is an interaction with 'init'.
    if arg == "init_radius":
        return 2
    defaults_for_method = DEFAULTS_LOOKUP["method"][method.name.lower()]
    try:
        item = next(filter(lambda item: item["name"] == arg, defaults_for_method))
    except StopIteration:
        raise ValueError(f"No argument `{arg}` is associated with `{method}`.")
    type = _pythonize_cmdstan_type(item["type"])
    if type == bool:
        # bool needs special handling because bool('0') == True
        return item["default"] != "0"
    return type(item["default"])


def function_arguments(function_name: str, model_module) -> typing.List[str]:
    """Get function arguments for stan::services `function_name`.

    A compiled `model_module` is required for the lookup. Only simple function
    arguments are returned. For example, callback writers and var_context
    arguments are dropped.

    Arguments:
        function_name: Name of the function.
        model_module (module): Compiled model module.

    Returns:
        Argument names for `function_name`.

    """
    function = getattr(model_module, f"{function_name}_wrapper")
    sig = inspect.Signature.from_callable(function)
    # remove arguments which are specific to the wrapper
    arguments_exclude = {"array_var_context_capsule", "queue_capsule"}
    return list(filter(lambda arg: arg not in arguments_exclude, sig.parameters))
