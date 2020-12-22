"""Runs the `stanc` binary in a subprocess to compile a Stan program."""
import importlib.resources
import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple, Union


def compile(program_code: str, stan_model_name: str) -> Tuple[str, str]:
    """Return C++ code for Stan model specified by `program_code`.

    Arguments:
        program_code
        stan_model_name

    Returns:
        (str, str): C++ code, stanc warnings

    Raises:
        ValueError: Syntax or semantic error in program code.

    """
    with importlib.resources.path(__package__, "stanc") as stanc_binary:
        with tempfile.TemporaryDirectory(prefix="httpstan_") as tmpdir:
            filepath = Path(tmpdir) / f"{stan_model_name}.stan"
            with filepath.open("w") as fh:
                fh.write(program_code)
            run_args: List[Union[os.PathLike, str]] = [
                stanc_binary,
                "--name",
                stan_model_name,
                "--warn-pedantic",
                "--print-cpp",
                str(filepath),
            ]
            completed_process = subprocess.run(run_args, capture_output=True, timeout=1)
    stderr = completed_process.stderr.decode().strip()
    if completed_process.returncode != 0:
        raise ValueError(stderr)
    return completed_process.stdout.decode().strip(), stderr
