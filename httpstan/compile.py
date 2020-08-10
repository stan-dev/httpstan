"""Runs the `stanc` binary in a subprocess to compile a Stan program."""
import importlib.resources
import os
import subprocess
import tempfile
from typing import List, Tuple, Union


def compile(program_code: str, stan_model_name: str) -> Tuple[str, str]:
    """Return C++ code for Stan model specified by `program_code`.

    Arguments:
        program_code
        stan_model_name

    Returns:
        (str, str): C++ code, warnings

    Raises:
        ValueError: Syntax or semantic error in program code.

    """
    with importlib.resources.path(__package__, "stanc") as stanc_binary:
        with tempfile.NamedTemporaryFile() as fh:
            fh.write(program_code.encode())
            fh.flush()
            run_args: List[Union[os.PathLike, str]] = [
                stanc_binary,
                "--name",
                stan_model_name,
                "--print-cpp",
                fh.name,
            ]
            completed_process = subprocess.run(run_args, capture_output=True, timeout=1)
    stderr = completed_process.stderr.decode().strip()
    if completed_process.returncode != 0:
        raise ValueError(stderr)
    return completed_process.stdout.decode().strip(), stderr
