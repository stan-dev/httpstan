"""Lookup arguments and argument default values for stan::services functions."""
import enum
import functools
import importlib.resources
import json
import re
import time
import types
import typing

Method = enum.Enum("Method", "SAMPLE OPTIMIZE VARIATIONAL DIAGNOSE")
DEFAULTS_LOOKUP = None  # lazy loaded by lookup_default


def _pythonize_cmdstan_type(type_name: str) -> type:
    """Turn CmdStan C++ type name into Python type.

    For example, "double" becomes ``float`` (the type).

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
        DEFAULTS_LOOKUP = json.loads(importlib.resources.read_text(__package__, "cmdstan-help-all.json"))
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
    python_type = _pythonize_cmdstan_type(item["type"])
    if python_type == bool:
        # bool needs special handling because bool("0") == True
        return int(item["default"] != "0")
    assert python_type in {int, float}
    return typing.cast(typing.Union[float, int], python_type(item["default"]))


def function_arguments(function_name: str, services_module: types.ModuleType) -> typing.List[str]:
    """Get function arguments for stan::services `function_name`.

    This function parses a function's docstring to get argument names. This is
    an inferior method to using `inspect.Signature.from_callable(function)`.
    Unfortunately, pybind11 does not support this use of `inspect`.

    A compiled `services_module` is required for the lookup. Only simple function
    arguments are returned. For example, callback writers and var_context
    arguments are dropped.

    Arguments:
        function_name: Name of the function.
        services_module (module): Compiled model-specific services extension module.

    Returns:
        Argument names for `function_name`.

    """
    function = getattr(services_module, f"{function_name}_wrapper")
    docstring = function.__doc__
    # first line look something like this: function_name(arg1: int, arg2: int, ...) -> int
    function_name_with_arguments = docstring.split(" -> ", 1).pop(0)
    parameters = re.findall(r"(\w+): \w+", function_name_with_arguments)
    # remove arguments which are specific to the wrapper
    arguments_exclude = {"socket_filename"}
    return list(filter(lambda arg: arg not in arguments_exclude, parameters))
