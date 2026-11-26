"""Build Windows httpstan dependencies, preserving Stan Math's source selection.

Run in an activated x64 MSVC-compatible toolchain prompt. Stage boundaries are
also used by windows_ci.py; do not use an existing dependency tree from another
compiler configuration for a release build.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "win"
PACKAGE = ROOT / "httpstan"
INCLUDE = PACKAGE / "include"
LIB = PACKAGE / "lib"

# Load the build helper without importing httpstan before installation.
spec = importlib.util.spec_from_file_location("httpstan_windows_build", PACKAGE / "_windows.py")
assert spec and spec.loader
win = importlib.util.module_from_spec(spec)
spec.loader.exec_module(win)


def version(name):
    for line in (ROOT / "Makefile").read_text().splitlines():
        if line.startswith(name + " := "):
            return line.split(":=", 1)[1].strip()
    raise RuntimeError(f"Version {name} not found")


STAN = version("STAN_VERSION")
MATH = version("MATH_VERSION")
BOOST = version("BOOST_VERSION")
EIGEN = version("EIGEN_VERSION")
SUNDIALS = version("SUNDIALS_VERSION")
TBB = version("TBB_VERSION")
STANC = version("STANC_VERSION")
RAPIDJSON = version("RAPIDJSON_VERSION")
# Windows only for the first experiment; leave the Unix Makefile unchanged.
PYBIND = "2.13.6"


def download(url, dest):
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_suffix(dest.suffix + ".part")
        win.run(["curl.exe", "--fail", "--location", "--retry", "5", "--silent", "--show-error",
                 "--output", str(part), url], ROOT)
        part.replace(dest)
    with dest.open("rb") as fh:
        digest = hashlib.file_digest(fh, "sha256").hexdigest()
    print(f"[download] {dest.name} bytes={dest.stat().st_size} sha256={digest}", flush=True)
    return dest


def github_archive(repo, tag, directory):
    if not directory.is_dir():
        path = download(f"https://github.com/{repo}/archive/refs/tags/{tag}.tar.gz", BUILD / "archives" / (directory.name + ".tar.gz"))
        with tarfile.open(path) as archive:
            archive.extractall(BUILD, filter="data")
    if not directory.is_dir():
        raise RuntimeError(f"Archive did not contain {directory}")
    return directory


def copy_tree(source, target):
    print(f"[headers] {source} -> {target}", flush=True)
    shutil.copytree(source, target, dirs_exist_ok=True)


def patch_sundials(root):
    # The vendored header was generated on a Unix compiler. Keep the index and
    # precision configuration unchanged; disable only POSIX timers and replace
    # deprecation syntax that MSVC does not understand.
    config = root / "include" / "sundials" / "sundials_config.h"
    export = root / "include" / "sundials" / "sundials_export.h"
    for path in (config, export):
        text = path.read_text(encoding="utf-8")
        changed = text.replace("__attribute__ ((__deprecated__(msg)))", "__declspec(deprecated(msg))")
        changed = changed.replace("__attribute__ ((__deprecated__))", "__declspec(deprecated)")
        changed = changed.replace("#define SUNDIALS_HAVE_POSIX_TIMERS\n", "/* #undef SUNDIALS_HAVE_POSIX_TIMERS */\n")
        if changed != text:
            path.write_text(changed, encoding="utf-8")
            print(f"[patch] {path}", flush=True)


def prepare():
    BUILD.mkdir(parents=True, exist_ok=True)
    INCLUDE.mkdir(parents=True, exist_ok=True)
    LIB.mkdir(parents=True, exist_ok=True)
    stan = github_archive("stan-dev/stan", "v" + STAN, BUILD / ("stan-" + STAN))
    math = github_archive("stan-dev/math", "v" + MATH, BUILD / ("math-" + MATH))
    pybind = github_archive("pybind/pybind11", "v" + PYBIND, BUILD / ("pybind11-" + PYBIND))
    rapid = github_archive("Tencent/rapidjson", "v" + RAPIDJSON, BUILD / ("rapidjson-" + RAPIDJSON))
    copy_tree(stan / "src/stan", INCLUDE / "stan")
    copy_tree(math / "stan/math", INCLUDE / "stan/math")
    shutil.copy2(math / "stan/math.hpp", INCLUDE / "stan/math.hpp")
    copy_tree(pybind / "include/pybind11", INCLUDE / "pybind11")
    copy_tree(rapid / "include/rapidjson", INCLUDE / "rapidjson")
    copy_tree(math / f"lib/boost_{BOOST}/boost", INCLUDE / "boost")
    for name in ("Eigen", "unsupported"):
        copy_tree(math / f"lib/eigen_{EIGEN}" / name, INCLUDE / name)
    copy_tree(math / f"lib/tbb_{TBB}/include/tbb", INCLUDE / "tbb")
    sundials = math / f"lib/sundials_{SUNDIALS}"
    patch_sundials(sundials)
    copy_tree(sundials / "include", INCLUDE)
    shutil.copy2(download(f"https://github.com/stan-dev/stanc3/releases/download/v{STANC}/windows-stanc",
                          BUILD / "archives/stanc.exe"), PACKAGE / "stanc.exe")
    win.run([str(PACKAGE / "stanc.exe"), "--version"], ROOT)
    # Official Windows release, not the MinGW library from CmdStan.
    archive = download(f"https://github.com/uxlfoundation/oneTBB/releases/download/v{TBB}/tbb-{TBB}-win.zip",
                       BUILD / "archives/tbb-win.zip")
    with zipfile.ZipFile(archive) as z:
        for name in ("tbb.dll", "tbb.lib"):
            candidates = [p for p in z.namelist() if p.lower().endswith("/" + name) and "/intel64/" in p.lower()]
            print(f"[tbb] {name} candidates={candidates}", flush=True)
            # vc14 is the VS2015+ ABI; a later vc14x directory is also compatible.
            candidates = [p for p in candidates if any(x.startswith("vc14") for x in p.lower().split("/"))]
            if not candidates:
                raise RuntimeError(f"No x64 vc14-family {name} in TBB release archive")
            selected = sorted(candidates, key=lambda p: ("/vc14/" not in p.lower(), p))[0]
            print(f"[tbb] selected {selected}", flush=True)
            with z.open(selected) as src, (LIB / name).open("wb") as dst:
                shutil.copyfileobj(src, dst)
        # Preserve release license alongside development binaries where available.
        for p in z.namelist():
            if p.rsplit("/", 1)[-1].lower() in {"license", "license.txt"}:
                (LIB / "TBB-LICENSE.txt").write_bytes(z.read(p))
                break
    win.run([win.tool("dumpbin"), "/headers", str(LIB / "tbb.dll")], ROOT)


def sundials(family):
    source = BUILD / f"math-{MATH}/lib/sundials_{SUNDIALS}"
    src = source / "src"
    objdir = BUILD / "sundials-obj"
    objdir.mkdir(exist_ok=True)
    common = [p for p in (src / "sundials").glob("*.c") if p.name != "sundials_profiler.c"]
    for folder in ("sunmatrix/band", "sunmatrix/dense", "sunlinsol/band", "sunlinsol/dense",
                   "sunnonlinsol/newton", "sunnonlinsol/fixedpoint"):
        common.extend(p for p in (src / folder).glob("*.c") if not p.name.startswith("f"))
    groups = {name: sorted(set(common + list((src / name).glob("*.c")))) for name in ("cvodes", "idas", "kinsol")}
    groups["nvecserial"] = [src / "nvector/serial/nvector_serial.c", src / "sundials/sundials_math.c"]
    for group, sources in groups.items():
        if not sources or not all(p.is_file() for p in sources):
            raise RuntimeError(f"Missing sources for {group}: {sources}")
        print(f"[sundials] {group}: {len(sources)} sources", flush=True)
    objects = {}
    for path in sorted(set(p for sources in groups.values() for p in sources)):
        obj = objdir / ("_".join(path.relative_to(src).parts) + ".obj")
        args = [win.compiler(family), "/nologo", "/TC", "/c", "/MD", "/O2", "/DNDEBUG",
                "/DSUNDIALS_STATIC_DEFINE", "/DNO_FPRINTF_OUTPUT", "/D_USE_MATH_DEFINES",
                "/I" + str(source / "include"), "/I" + str(src / "sundials"),
                "/FI" + str(source / "include/stan_sundials_printf_override.hpp"), str(path), "/Fo" + str(obj)]
        if family == "cl":
            args.insert(3, "/std:c11")
        win.run(args, objdir)
        objects[path] = obj
    for group, sources in groups.items():
        target = LIB / ("sundials_" + group + ".lib")
        target.unlink(missing_ok=True)
        win.run([win.tool("lib"), "/NOLOGO", "/OUT:" + str(target), *[str(objects[p]) for p in sources]], objdir)


def smoke_headers(family, optimization):
    # Two small programs: first header compilation, then full Math header and
    # reverse-mode derivative (compile only before linking dependencies).
    for name, code in (
        ("prim", '#include <stan/math/prim.hpp>\nint main(){return stan::math::square(2.0)==4.0?0:1;}\n'),
        ("math", '#include <stan/math.hpp>\nint main(){stan::math::var x=2.0; auto y=x*x; y.grad(); return x.adj()==4.0?0:1;}\n'),
    ):
        path = BUILD / (name + ".cpp")
        path.write_text(code, encoding="utf-8")
        win.compile_cpp(family, path, path.with_suffix(".obj"), optimization)


def smoke_link(family):
    # Test actual runtime linkage and the derivative, not only header parsing.
    exe = BUILD / "math.exe"
    win.run([win.tool("link"), "/NOLOGO", "/MACHINE:X64", "/OUT:" + str(exe), str(BUILD / "math.obj"),
             *[str(LIB / (name + ".lib")) for name in win.LIBRARIES], *win.clang_link_args(family)], BUILD)
    shutil.copy2(LIB / "tbb.dll", BUILD / "tbb.dll")
    win.run([str(exe)], BUILD)


def services(family, optimization):
    win.compile_cpp(family, PACKAGE / "stan_services.cpp", PACKAGE / "stan_services.obj", optimization)
    with (PACKAGE / "stan_services.obj").open("rb") as fh:
        services_digest = hashlib.file_digest(fh, "sha256").hexdigest()
    config = {"compiler": family, "optimization": optimization, "python": f"{sys.version_info.major}.{sys.version_info.minor}",
              "stan": STAN, "math": MATH, "pybind11": PYBIND, "tbb": TBB, "sundials": SUNDIALS,
              "msvc_version": os.environ.get("VCToolsVersion", "unknown"),
              "sdk_version": os.environ.get("WindowsSDKVersion", "unknown").rstrip("\\"),
              "services_sha256": services_digest}
    if family == "clang-cl":
        config["clang_version"] = subprocess.check_output([win.compiler(family), "--version"], text=True).splitlines()[0]
    win.MANIFEST.write_text(json.dumps(config, indent=2, sort_keys=True), encoding="utf-8")
    print(win.MANIFEST.read_text(), flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=["prepare", "headers", "sundials", "link", "services", "all"])
    p.add_argument("--compiler", choices=["cl", "clang-cl"], required=True)
    p.add_argument("--optimization", choices=["O2", "Od"], default="O2")
    args = p.parse_args()
    if sys.platform != "win32" or sys.maxsize <= 2**32:
        raise SystemExit("Windows x64 CPython required")
    opt = "/" + args.optimization
    stages = [("prepare", prepare), ("headers", lambda: smoke_headers(args.compiler, opt)),
              ("sundials", lambda: sundials(args.compiler)), ("link", lambda: smoke_link(args.compiler)),
              ("services", lambda: services(args.compiler, opt))]
    for name, func in stages:
        if args.stage in (name, "all"):
            print(f"=== {name.upper()} compiler={args.compiler} optimization={opt} ===", flush=True)
            func()


if __name__ == "__main__":
    main()
