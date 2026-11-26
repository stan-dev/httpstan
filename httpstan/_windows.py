"""Experimental Windows native build helpers (MSVC ABI, x64).

The precompiled service object and generated model use the same compiler family
and flags. Call from a VS developer prompt or a portable setup_x64.bat prompt.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import time
import uuid
from pathlib import Path
from typing import List

PACKAGE_DIR = Path(__file__).resolve().parent
MANIFEST = PACKAGE_DIR / "windows-build.json"
MACROS = (
    "BOOST_DISABLE_ASSERTS",
    "BOOST_PHOENIX_NO_VARIADIC_EXPRESSION",
    "BOOST_ALL_NO_LIB",
    "__TBB_NO_IMPLICIT_LINKAGE=1",
    "STAN_THREADS",
    "NOMINMAX",
    "WIN32_LEAN_AND_MEAN",
    "_USE_MATH_DEFINES",
    "_BOOST_LGAMMA=1",
    "SUNDIALS_STATIC_DEFINE",
    "_ITERATOR_DEBUG_LEVEL=0",
)
LIBRARIES = ("sundials_cvodes", "sundials_idas", "sundials_nvecserial", "sundials_kinsol", "tbb")


def compiler(family: str) -> str:
    if family not in {"cl", "clang-cl"}:
        raise ValueError(f"Unsupported Windows compiler: {family}")
    path = shutil.which(family + ".exe")
    if path is None:
        raise RuntimeError(f"{family}.exe not found; activate a VS or portable developer prompt first")
    return path


def tool(name: str) -> str:
    path = shutil.which(name + ".exe")
    if path is None:
        raise RuntimeError(f"{name}.exe not found; activate the toolchain first")
    return path


def flags(family: str, optimization: str = "/O2") -> List[str]:
    args = ["/nologo", "/std:c++17", "/EHsc", "/MD", "/bigobj", "/Zc:__cplusplus", optimization]
    # Preserve IEEE semantics, no fast-math or link-time code generation.
    args += ["/fp:precise", "/DNDEBUG"]
    if family == "cl":
        args += ["/permissive-", "/utf-8"]
    return args + ["/D" + macro for macro in MACROS]


def run(command: List[str], cwd: Path) -> str:
    """Print exact compiler invocation, stream merged diagnostics, retain output."""
    invocation = subprocess.list2cmdline([str(arg) for arg in command])
    print(f"[native] cwd={cwd}\n[native] {invocation}", flush=True)
    start = time.monotonic()
    lines = []
    with subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    ) as process:
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="", flush=True)
            lines.append(line)
        status = process.wait()
    elapsed = time.monotonic() - start
    print(f"[native] exit={status} elapsed={elapsed:.2f}s", flush=True)
    output = invocation + "\n" + "".join(lines)
    if status:
        raise RuntimeError(f"Native command failed ({status}):\n{output[-30000:]}")
    return output


def clang_link_args(family: str) -> List[str]:
    if family != "clang-cl":
        return []
    resource = Path(subprocess.check_output([compiler(family), "--print-resource-dir"], text=True).strip())
    directory = resource / "lib" / "windows"
    if not directory.is_dir():
        return []
    args = ["/LIBPATH:" + str(directory)]
    builtins = directory / "clang_rt.builtins-x86_64.lib"
    if builtins.is_file():
        args.append(str(builtins))
    return args


def python_import_lib() -> Path:
    name = f"python{sys.version_info.major}{sys.version_info.minor}.lib"
    candidates = [Path(sys.base_prefix) / "libs" / name, Path(sys.prefix) / "libs" / name]
    for path in candidates:
        if path.is_file():
            return path
    raise RuntimeError(f"Cannot find CPython import library {name}: {candidates}")


def compile_cpp(family: str, source: Path, target: Path, optimization: str = "/O2") -> str:
    return run(
        [
            compiler(family),
            *flags(family, optimization),
            "/I" + str(PACKAGE_DIR / "include"),
            "/I" + sysconfig.get_path("include"),
            "/c",
            str(source),
            "/Fo" + str(target),
        ],
        target.parent,
    )


def read_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def cache_identity() -> bytes:
    # Exclude absolute toolchain paths from the persistent model identifier.
    return hashlib.sha256(MANIFEST.read_bytes()).digest()


def build_model(source: Path, directory: Path, extra_compile_args: List[str]) -> str:
    config = read_manifest()
    family = config["compiler"]
    optimization = config["optimization"]
    override = os.environ.get("HTTPSTAN_WINDOWS_CXX")
    if override and override != family:
        raise RuntimeError(f"Wheel uses {family}, not {override}; rebuild the service object to change compiler")
    # A unique filename makes deletion/recompilation independent of loaded DLLs.
    obj = directory / (source.stem + ".obj")
    target = directory / ("stan_services_" + source.stem + "_" + uuid.uuid4().hex[:12] + ".pyd")
    args = [
        compiler(family),
        *flags(family, optimization),
        *extra_compile_args,
        "/I" + str(PACKAGE_DIR / "include"),
        "/I" + sysconfig.get_path("include"),
        "/c",
        str(source),
        "/Fo" + str(obj),
    ]
    output = run(args, directory)
    # Explicit linking avoids setuptools deriving an incorrect PyInit name and
    # avoids private distutils compiler-selection interfaces for clang-cl.
    # Publish only after a successful link: a failed link must not leave a
    # partially written .pyd that the cache mistakes for a valid module.
    with tempfile.TemporaryDirectory(prefix="link-", dir=directory) as tmp:
        staged = Path(tmp) / target.name
        output += run(
            [
                tool("link"),
                "/NOLOGO",
                "/DLL",
                "/MACHINE:X64",
                "/INCREMENTAL:NO",
                "/OUT:" + str(staged),
                str(obj),
                str(PACKAGE_DIR / "stan_services.obj"),
                str(python_import_lib()),
                *[str(PACKAGE_DIR / "lib" / (name + ".lib")) for name in LIBRARIES],
                "Ws2_32.lib",
                *clang_link_args(family),
            ],
            directory,
        )
        staged.replace(target)
    return output
