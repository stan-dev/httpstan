"""Runs the `stanc` binary in a subprocess to compile a Stan program."""
import importlib.resources
import subprocess
import tempfile


def compile(program_code: str, stan_model_name: str) -> str:
    """Return C++ code for Stan model specified by `program_code`.

    Arguments:
        program_code
        stan_model_name

    Returns:
        str: C++ code

    Raises:
        ValueError: Syntax or semantic error in program code.

    """
    with importlib.resources.path(__package__, "stanc") as stanc_binary:
        with tempfile.NamedTemporaryFile() as fh:
            fh.write(program_code.encode())
            fh.flush()
            run_args = [
                stanc_binary,
                "--name",
                stan_model_name,
                "--print-cpp",
                fh.name,
            ]
            completed_process = subprocess.run(run_args, capture_output=True, timeout=1)
    stderr = completed_process.stderr.decode()
    if stderr:
        # `strip` unnecessary newlines in stanc error message
        raise ValueError(stderr.strip())

    return completed_process.stdout.decode().strip()
