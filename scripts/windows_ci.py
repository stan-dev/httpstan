"""Run the Windows experiment in stages, retaining each stage's raw output.

This script is used by .github/workflows/windows.yml. It can also be run from
an ordinary Windows cmd.exe with Python 3.12 installed.
"""
import argparse
import hashlib
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import traceback
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "windows-logs"
BUILD = ROOT / "build" / "win"
# Raw revision identified from the author's Gist, not a moving latest script.
PORTABLE_URL = (
    "https://gist.githubusercontent.com/mmozeiko/7f3162ec2988e81e56d5c4e22cde9977/"
    "raw/49b58850aa5e5c1e65f090d4651ee76607883e11/portable-msvc.py"
)
PROFILES = ("official-clang", "official-msvc", "portable-clang", "portable-msvc", "official-clang-od", "official-msvc-od")


def stage(name, command, cwd=ROOT, env=None):
    LOGS.mkdir(exist_ok=True)
    command = [str(x) for x in command]
    if not Path(command[0]).is_absolute():
        executable = shutil.which(command[0], path=(env or os.environ).get("PATH"))
        if executable:
            command[0] = executable
    path = LOGS / (name + ".log")
    start = time.monotonic()
    invocation = subprocess.list2cmdline([str(x) for x in command])
    print(f"\n=== STAGE {name} ===\n{invocation}", flush=True)
    with path.open("w", encoding="utf-8") as log:
        log.write(f"cwd={cwd}\n{invocation}\n")
        log.flush()
        with subprocess.Popen(command, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, encoding="utf-8", errors="replace") as process:
            for line in process.stdout:
                print(line, end="", flush=True)
                log.write(line)
                log.flush()
            status = process.wait()
        result = f"=== STAGE {name} {'PASS' if status == 0 else 'FAIL'} exit={status} seconds={time.monotonic()-start:.1f} ==="
        print(result, flush=True)
        log.write(result + "\n")
    with (LOGS / "summary.txt").open("a", encoding="utf-8") as summary:
        summary.write(result + "\n")
    if status:
        raise SystemExit(status)


def activate_batch(batch, args, env):
    # Do not print `set`: inherited CI environment may contain secrets.
    script = BUILD / "activate.cmd"
    activation_log = LOGS / "toolchain-activation.log"
    script.write_text(f'@echo off\ncall "{batch}" {args} > "{activation_log}" 2>&1\n'
                      'if errorlevel 1 exit /b 1\nset\n', encoding="mbcs")
    result = subprocess.run(["cmd.exe", "/d", "/c", "call", str(script)], env=env, cwd=ROOT,
                            capture_output=True, text=True, encoding="oem", errors="replace")
    if activation_log.exists():
        print(activation_log.read_text(encoding="utf-8", errors="replace"), flush=True)
    result.check_returncode()
    activated = {}
    for line in result.stdout.splitlines():
        if "=" in line and not line.startswith("="):
            key, value = line.split("=", 1)
            activated[key.upper()] = value
    return activated


def configure(profile):
    env = os.environ.copy()
    llvm = shutil.which("clang-cl.exe")
    if not llvm:
        candidate = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "LLVM/bin/clang-cl.exe"
        if candidate.is_file():
            llvm = str(candidate)
    if profile.startswith("portable"):
        # No silent license acceptance. Repository owner opts in after review.
        if env.get("HTTPSTAN_ACCEPT_MSVC_LICENSE", "").lower() != "yes":
            raise SystemExit("Portable job requires repository variable HTTPSTAN_ACCEPT_MSVC_LICENSE=yes after reviewing the Microsoft license.")
        portable = BUILD / "portable"
        portable.mkdir(exist_ok=True)
        script = portable / "portable-msvc.py"
        stage("01-download-portable", ["curl.exe", "--fail", "--location", "--retry", "5", "--output", str(script), PORTABLE_URL])
        print("Portable script SHA256:", hashlib.sha256(script.read_bytes()).hexdigest(), flush=True)
        stage("02-portable-versions", [sys.executable, str(script), "--vs", "2022", "--show-versions"], cwd=portable)
        args = [sys.executable, str(script), "--vs", "2022", "--target", "x64", "--host", "x64", "--accept-license"]
        if env.get("HTTPSTAN_PORTABLE_MSVC_VERSION"):
            args += ["--msvc-version", env["HTTPSTAN_PORTABLE_MSVC_VERSION"]]
        if env.get("HTTPSTAN_PORTABLE_SDK_VERSION"):
            args += ["--sdk-version", env["HTTPSTAN_PORTABLE_SDK_VERSION"]]
        stage("03-portable-install", args, cwd=portable)
        # Remove all conventional VS/SDK paths before activation, not after.
        for key in tuple(env):
            if key.upper() in {"INCLUDE", "LIB", "LIBPATH", "VCINSTALLDIR", "VSINSTALLDIR", "VCTOOLSINSTALLDIR",
                               "VCTOOLSVERSION", "WINDOWSSDKDIR", "WINDOWSSDKVERSION", "UNIVERSALCRTSDKDIR", "UCRTVERSION"} or key.upper().startswith("VSCMD_"):
                env.pop(key)
        env["PATH"] = os.pathsep.join(p for p in env["PATH"].split(os.pathsep)
                                     if "microsoft visual studio" not in p.lower() and "windows kits" not in p.lower())
        root = (portable / "msvc").resolve()
        env = activate_batch(root / "setup_x64.bat", "", env)
        for name in ("cl.exe", "link.exe", "lib.exe", "dumpbin.exe"):
            actual = shutil.which(name, path=env["PATH"])
            if not actual or not Path(actual).resolve().is_relative_to(root):
                raise RuntimeError(f"Portable {name} was not resolved inside {root}: {actual}")
        for key in ("INCLUDE", "LIB"):
            for value in env.get(key, "").split(os.pathsep):
                if value and not Path(value).resolve().is_relative_to(root):
                    raise RuntimeError(f"Portable {key} contains external path: {value}")
    else:
        vswhere = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Microsoft Visual Studio/Installer/vswhere.exe"
        root = subprocess.check_output([str(vswhere), "-latest", "-products", "*", "-version", "[17.0,18.0)",
                                        "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                                        "-property", "installationPath"], text=True).strip()
        if not root:
            raise RuntimeError("Visual Studio 2022 C++ Build Tools not found")
        env = activate_batch(Path(root) / "VC/Auxiliary/Build/vcvars64.bat", "", env)
    if "clang" in profile:
        # Use the same LLVM installation for both clang profiles.
        if not llvm:
            raise RuntimeError("clang-cl not found; install LLVM or add clang-cl.exe to PATH")
        env["PATH"] = str(Path(llvm).parent) + os.pathsep + env["PATH"]
    # Make the dummy setuptools extension use the already activated toolchain.
    env["DISTUTILS_USE_SDK"] = "1"
    env["MSSDK"] = "1"
    env["PYTHONUTF8"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    # Do not inherit arbitrary external compiler flags that change the ABI.
    for name in ("CL", "_CL_", "LINK", "_LINK_", "CC", "CXX", "CFLAGS", "CXXFLAGS", "LDFLAGS", "PYTHONPATH"):
        env.pop(name, None)
    info = {"profile": profile, "python": sys.version, "executable": sys.executable, "platform": platform.platform(),
            "cpu_count": os.cpu_count(), "AF_UNIX": hasattr(socket, "AF_UNIX"),
            "tools": {name: shutil.which(name + ".exe", path=env["PATH"]) for name in ("cl", "clang-cl", "link", "lib", "dumpbin")},
            "INCLUDE": env.get("INCLUDE"), "LIB": env.get("LIB"), "VCToolsVersion": env.get("VCTOOLSVERSION"),
            "WindowsSDKVersion": env.get("WINDOWSSDKVERSION"), "VCToolsInstallDir": env.get("VCTOOLSINSTALLDIR"),
            "ImageVersion": env.get("IMAGEVERSION"), "ImageOS": env.get("IMAGEOS")}
    text = json.dumps(info, indent=2)
    print(text, flush=True)
    (LOGS / "toolchain.json").write_text(text, encoding="utf-8")
    return env


def validate_wheel(wheel):
    with zipfile.ZipFile(wheel) as archive:
        files = set(archive.namelist())
        required = {"httpstan/stanc.exe", "httpstan/stan_services.obj", "httpstan/windows-build.json",
                    "httpstan/lib/tbb.dll", "httpstan/lib/tbb.lib", "httpstan/lib/sundials_cvodes.lib",
                    "httpstan/lib/sundials_idas.lib", "httpstan/lib/sundials_nvecserial.lib", "httpstan/lib/sundials_kinsol.lib",
                    "httpstan/include/stan/math.hpp", "httpstan/include/pybind11/pybind11.h", "httpstan/include/boost/version.hpp",
                    "httpstan/include/Eigen/Core", "httpstan/include/tbb/tbb.h", "httpstan/include/rapidjson/document.h"}
        missing = required - files
        if missing or not wheel.name.endswith("win_amd64.whl"):
            raise RuntimeError(f"Wrong wheel tag or missing wheel contents: {wheel.name}, {sorted(missing)}")
        print(f"[wheel] {wheel.name} size={wheel.stat().st_size} members={len(files)}", flush=True)
        (LOGS / "wheel-files.txt").write_text("\n".join(sorted(files)), encoding="utf-8")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--profile", choices=PROFILES, required=True)
    p.add_argument("--through", choices=["headers", "services", "smoke", "full"], default="smoke")
    args = p.parse_args()
    if sys.platform != "win32" or sys.version_info[:2] != (3, 12) or sys.maxsize <= 2**32:
        raise SystemExit("First-round experiments require Windows x64 and CPython 3.12")
    LOGS.mkdir(exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)
    (LOGS / "summary.txt").write_text(f"profile={args.profile} through={args.through}\n", encoding="utf-8")
    env = configure(args.profile)
    family = "clang-cl" if "clang" in args.profile else "cl"
    opt = "Od" if args.profile.endswith("-od") else "O2"
    stage("04-compiler-version", [env["COMSPEC"], "/d", "/c", "cl /Bv 2>&1 & exit /b 0"], env=env)
    if family == "clang-cl":
        stage("05-clang-version", ["clang-cl.exe", "--version"], env=env)
    stage("09-socket-smoke", [sys.executable, str(ROOT / "scripts/windows_socket_smoke.py"), "--compiler", family], env=env)
    native = [sys.executable, str(ROOT / "scripts/build_windows.py")]
    for number, name in enumerate(("prepare", "headers", "sundials", "link", "services"), 10):
        stage(f"{number}-{name}", [*native, name, "--compiler", family, "--optimization", opt], env=env)
        if args.through == name:
            return
    stage("20-install-build-tools", [sys.executable, "-m", "pip", "install", "poetry~=1.8.0", "setuptools<81"], env=env)
    stage("21-wheel", [sys.executable, "-m", "poetry", "build", "-f", "wheel", "-v"], env=env)
    wheels = sorted((ROOT / "dist").glob("*.whl"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not wheels:
        raise RuntimeError("No wheel produced")
    wheel = wheels[0].resolve()
    validate_wheel(wheel)
    # Fresh virtual environment: no source package or build-time Python dependencies.
    test_root = Path(tempfile.mkdtemp(prefix="httpstan-test-", dir=os.environ.get("RUNNER_TEMP")))
    print(f"[test] isolated test directory: {test_root}", flush=True)
    venv = test_root / "venv"
    stage("22-test-venv", [sys.executable, "-m", "venv", str(venv)], env=env)
    py = str(venv / "Scripts/python.exe")
    stage("23-install-wheel", [py, "-m", "pip", "install", str(wheel), "pytest>=8.3,<9", "pytest-asyncio>=0.24,<0.25", "apispec[yaml]>=6,<7"], env=env)
    stage("24-import-wheel", [py, "-c", "import sys, pathlib, httpstan, httpstan.app, httpstan.empty; print(httpstan.__file__); print(httpstan.__version__); assert pathlib.Path(httpstan.__file__).resolve().is_relative_to(pathlib.Path(sys.prefix).resolve()); httpstan.empty.noop()"], cwd=test_root, env=env)
    # Copy tests outside the source repo so pytest cannot accidentally import the source tree.
    tests = test_root / "installed-tests"
    shutil.copytree(ROOT / "tests", tests, dirs_exist_ok=True)
    smoke = [str(tests / name) for name in ("test_health_check.py", "test_windows_smoke.py", "test_cvodes.py", "test_fixed_param.py", "test_log_prob_grad.py")]
    stage("25-runtime-smoke", [py, "-m", "pytest", "-s", "-vv", "--log-cli-level=INFO", "--asyncio-mode=auto", *smoke], cwd=test_root, env=env)
    if args.through == "full":
        stage("26-full-pytest", [py, "-m", "pytest", "-s", "-vv", "--log-cli-level=INFO", "--asyncio-mode=auto", str(tests)], cwd=test_root, env=env)
    # Install PyStan from PyPI while forcing the local httpstan wheel, so pip cannot
    # replace it with a different build. If unavailable, report that separately.
    stage("27-install-pystan", [py, "-m", "pip", "install", "--pre", "pystan==3.14.0", str(wheel)], cwd=test_root, env=env)
    client = test_root / "pystan_smoke.py"
    shutil.copy2(ROOT / "scripts/pystan_windows_smoke.py", client)
    stage("28-pystan", [py, str(client)], cwd=test_root, env=env)
    print("=== ALL REQUESTED STAGES PASSED ===", flush=True)


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        LOGS.mkdir(exist_ok=True)
        with (LOGS / "summary.txt").open("a", encoding="utf-8") as log:
            log.write(f"STOP: {type(exc).__name__}: {exc}\n")
        if not isinstance(exc, SystemExit):
            (LOGS / "failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
