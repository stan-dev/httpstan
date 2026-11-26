# httpstan Windows experiments — round 1

Base: uploaded httpstan-main.zip, upstream commit `b00235f210a0b3f0e18c2212aef7524a4d9da0f1`, httpstan 4.17.0. Experimental, not a release or a verified Windows port.

## First run in GitHub Actions

From a clean clone of your fork (cmd.exe):

```bat
git switch -c windows-base b00235f210a0b3f0e18c2212aef7524a4d9da0f1
git apply --check C:\path\httpstan-windows-round1.patch
git apply C:\path\httpstan-windows-round1.patch
git add -A
git commit -m "Experimental Windows httpstan build and test profiles"
```

Review the diff before committing. Alternatively, extract the overlay ZIP into the repository root (including `.github/`), overwriting the listed files, then commit. Do not use both methods. If the exact base has moved, apply to the stated commit first; rebase later.

Enable Actions on the fork. `.github/workflows/main.yml` is unchanged; the original Linux/macOS workflow may also run on each experimental branch. Disable that workflow **on the fork** if you only want Windows runs. (The upstream `macos-14` hosted runner was retired in November 2026; unrelated to this patch.)

To run the official toolchains first:

```bat
git push origin HEAD:refs/heads/windows-test/official-clang
git push origin HEAD:refs/heads/windows-test/official-msvc
```

For the portable route, review the Microsoft Visual Studio license and the pinned third-party installer script at https://gist.github.com/mmozeiko/7f3162ec2988e81e56d5c4e22cde9977. Set the **repository variable** `HTTPSTAN_ACCEPT_MSVC_LICENSE` to `yes` under Settings -> Secrets and variables -> Actions -> Variables only if you accept the terms. Then:

```bat
git push origin HEAD:refs/heads/windows-test/portable-clang
git push origin HEAD:refs/heads/windows-test/portable-msvc
```

These are four different remote branches with a shared commit; the workflow selects its profile by branch name. No default-branch workflow-dispatch setup is required for push triggers. To create only one branch with all four parallel jobs, push `HEAD:refs/heads/windows-test/all` instead. Do not run both forms unless you want duplicate jobs.

## Profiles

| Branch suffix | Microsoft toolchain | Compiler | C++ optimization |
| --- | --- | --- | --- |
| `official-clang` | preinstalled VS2022, x64 SDK | clang-cl | /O2 |
| `official-msvc` | preinstalled VS2022, x64 SDK | cl | /O2 |
| `portable-clang` | extracted standalone MSVC + SDK, VS2022 channel | clang-cl | /O2 |
| `portable-msvc` | extracted standalone MSVC + SDK, VS2022 channel | cl | /O2 |
| `official-clang-od` | preinstalled VS2022 | clang-cl | /Od |
| `official-msvc-od` | preinstalled VS2022 | cl | /Od |

The /Od profiles are diagnostic fallback only (potentially very slow sampling); use them if optimization runs out of RAM or triggers compiler failures. All build genuine Windows x64 PE/COFF binaries and use Microsoft's linker and dynamic release CRT. No MinGW, WSL, or WASM. Both Clang profiles use the same runner-provided LLVM installation, so the portable comparison isolates the Microsoft libraries and tools. The dummy Poetry platform-tag extension is compiled by MSVC via setuptools even in the Clang profiles; the actual Stan/SUNDIALS/model code uses the selected compiler.

Add `-headers`, `-services` or `-full` to a branch suffix to stop after header tests, stop after precompiled services, or run all upstream tests, respectively. Example `windows-test/official-clang-full`. Default is `smoke`, which also builds and installs a wheel and runs targeted regression tests plus PyStan. Once the workflow exists on the default branch, `workflow_dispatch` also supports these selections.

Optional repository variables for portable profiles: `HTTPSTAN_PORTABLE_MSVC_VERSION` (e.g. 14.44 if present in list) and `HTTPSTAN_PORTABLE_SDK_VERSION` (e.g. 26100 if present). Without them the pinned installer selects available versions from the VS2022 channel. Actual tool paths, versions, include and library directories are logged. The portable test fails rather than silently falling back to installed Visual Studio. Hosted Windows runners are not proof of no-admin operation; test on a standard-user Windows account later.

## What the workflow does

1. Configure official or portable x64 MSVC ABI toolchain; log compiler and SDK versions and paths. Portable extraction is performed by a revision-pinned script. Its SHA-256 is printed; SDK/compiler versions can be further pinned using the variables above.
2. Compile/link/execute a small C++ Winsock callback test **before** Stan is downloaded; check token and 65,536-byte payload. `/showIncludes` verifies the SDK include paths.
3. Fetch Stan 2.39.0, Stan Math 5.3.0, Boost/Eigen/SUNDIALS/TBB matching Makefile, RapidJSON 1.1.0, pybind11 2.13.6 (Windows only), stanc.exe and TBB 2020.3 Windows binaries. Log downloaded archive sizes and SHA-256 checksums, selected TBB libraries, binary architecture, stanc version.
4. Compile `stan/math/prim.hpp`, then `stan/math.hpp` with reverse-mode differentiation (compile-only).
5. Build the vendored SUNDIALS C sources into MSVC-compatible `.lib` files, reproducing the Makefile source groups and forced printf override. Adjust the vendored config headers to MSVC deprecation syntax and disable unavailable POSIX timers; do not change precision/index type.
6. Link and run the derivative test against TBB and SUNDIALS.
7. Compile `stan_services.obj` with the selected flags. Save `windows-build.json` with compiler/versions and services object digest. This changes Windows model cache identity when the native build changes.
8. Build a platform-specific wheel with Poetry. Check that the wheel really contains the native binaries, headers, object and manifest. Upload the wheel if created, even if runtime tests fail.
9. Create a fresh virtual environment outside the checkout, install the wheel and modern test dependencies, verify import from the installed wheel, not the source tree. Keep the toolchain environment active because model compilation still requires it.
10. Test health endpoint, two different model DLLs, concurrent chains, cached model deletion/recompilation/resampling, CVODES compile, fixed-parameter sampling, log-probability gradient. Optionally run the complete upstream suite. Install PyStan 3.14.0 with the local wheel and run two chains.

Every native command and its combined stdout/stderr, return code, and timing is printed. No token or full environment dump is printed. Actions uploads `windows-logs-<profile>` even on failure, including `summary.txt`, `toolchain.json`, `NN-<stage>.log` and `failure.txt` if relevant. The job stops on the first failed stage so later output doesn't obscure the real failure. Download the diagnostic artifact or paste the raw failed stage and `toolchain.json` (plus summary). If the compiler prints a long chain of template errors, include the first error and the template context above and below it. Share artifacts from failing profiles even if another profile succeeds.

Artifacts `httpstan-wheel-<profile>` are **experimental wheels**, not release artifacts. Do not distribute them as production wheels until licenses and build reproducibility are checked. These artifacts never include the MSVC compiler or Windows SDK installer. The PyInstaller stage is intentionally not implemented until native builds are confirmed.

## Local official installation

From an elevated cmd.exe with the official Visual Studio 2022 Build Tools bootstrapper:

```bat
curl.exe -L --fail https://aka.ms/vs/17/release/vs_BuildTools.exe -o vs_BuildTools.exe
vs_BuildTools.exe --add Microsoft.VisualStudio.Workload.VCTools --add Microsoft.VisualStudio.Component.VC.Llvm.Clang --add Microsoft.VisualStudio.Component.VC.Llvm.ClangToolset --includeRecommended --passive --wait --norestart
```

After installation (ordinary cmd.exe, assuming default installation path):

```bat
call "%ProgramFiles(x86)%\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
where cl
where clang-cl
where link
where lib
cl
clang-cl --version
```

You can also run the CI orchestrator locally with ordinary Python 3.12 x64, from your repository root (it locates VS2022 with vswhere):

```bat
python scripts\windows_ci.py --profile official-clang --through headers
```

Use `--through smoke` for the full round-one process. Use a fresh clone/worktree per profile, especially if rerunning a different compiler. The workflow never needs to run the VS installer on the hosted runner.

## Local standalone installation (no VS installer)

Create a writable directory, e.g. `%USERPROFILE%\stan-toolchain`. Obtain and inspect the exact script:

```bat
mkdir "%USERPROFILE%\stan-toolchain"
cd /d "%USERPROFILE%\stan-toolchain"
curl.exe -L --fail https://gist.githubusercontent.com/mmozeiko/7f3162ec2988e81e56d5c4e22cde9977/raw/49b58850aa5e5c1e65f090d4651ee76607883e11/portable-msvc.py -o portable-msvc.py
python portable-msvc.py --vs 2022 --show-versions
python portable-msvc.py --vs 2022 --host x64 --target x64
call msvc\setup_x64.bat
where cl
where link
```

The standalone extractor asks you to accept Microsoft's license. This is an unofficial method; obey the license and don't redistribute the toolchain indiscriminately. If you already have LLVM installed, add its bin directory to PATH. Alternatively, LLVM 20.1.8 provides a portable archive (large download, no installer):

```bat
curl.exe -L --fail https://github.com/llvm/llvm-project/releases/download/llvmorg-20.1.8/clang+llvm-20.1.8-x86_64-pc-windows-msvc.tar.xz -o llvm.tar.xz
certutil -hashfile llvm.tar.xz SHA256
mkdir llvm
tar -xf llvm.tar.xz -C llvm --strip-components=1
set "PATH=%CD%\llvm\bin;%PATH%"
clang-cl --version
```

Check LLVM's release hash (for this exact archive: `f229769f11d6a6edc8ada599c0cda964b7dee6ab1a08c6cf9dd7f513e85b107f`) before extracting. In CI, LLVM is already present, so the portable profiles don't need the large LLVM download. To run the CI script for the standalone route, from a fresh repository worktree and after reviewing/accepting the Microsoft license:

```bat
set HTTPSTAN_ACCEPT_MSVC_LICENSE=yes
python scripts\windows_ci.py --profile portable-clang --through headers
```

This orchestrator downloads/extracts the MSVC toolchain into `build\win\portable\msvc` even if you have already set up a separate local standalone installation. To use your separately activated toolchain directly, use `python scripts\build_windows.py all --compiler clang-cl` followed by `python -m pip install "poetry~=1.8.0"` and `python -m poetry build -f wheel` (run `set DISTUTILS_USE_SDK=1` first). Use `--compiler cl` to test MSVC. To install an experimental wheel from Actions, activate the same toolchain first, then run `python -m pip install C:\path\the-wheel.whl` from the desired Python 3.12 x64 environment. Runtime compiler family and compatible toolset must match the wheel. The Python import library (`python312.lib`) and development headers must also be available. On Windows, models remain compiled at runtime; a wheel alone is not a compiler-free solution.

## Decisions and limitations

- Source basis is the exact provided ZIP. Only the Windows workflow is new; the existing main workflow and Unix build Makefile are unchanged.
- The C++ model link step uses explicit `link.exe` rather than relying on setuptools' extension-name-based export or private compiler-selection APIs. pybind11 exports `PyInit_stan_services` itself. The Python 3.12 Windows wheel precompiles a service object, then links it with each model object at runtime. `/MD`, C++17, `_ITERATOR_DEBUG_LEVEL=0`, no LTO/fast-math, and matching macro sets are deliberate. Clang's Windows resource library path is added if available. Arbitrary ABI-changing custom compiler flags are not tested.
- CPython on Windows does not reliably expose AF_UNIX. Windows native callback transport is authenticated loopback TCP, not an externally exposed port. Each connection sends a per-operation random token before its existing JSON lines. The public REST interface is unchanged. POSIX socket client is retained. This is an initial trusted-local deployment, not a hardened multi-user network service.
- Windows multiprocessing uses a lazily created `spawn` pool. Guard normal scripts with `if __name__ == '__main__':`; Jupyter and process shutdown need additional testing. Windows debug path sends from a thread to avoid blocking its callback reader.
- Windows model DLLs are copied into unique per-process `loaded` directories before import so the canonical cache can be deleted and rebuilt. Native DLLs remain loaded until process exit. Stale copies are **not automatically removed in this prototype**; after all httpstan processes are closed, remove the `loaded` subdirectory under `httpstan.cache.cache_directory()` if needed. Do not remove it while the server or workers run. Concurrent compilation/deletion of the same model by multiple clients needs more testing. Failed native links do not publish a partial `.pyd`.
- Windows-specific pybind11 upgrade to 2.13.6 avoids Python 3.12 header incompatibility. Upstream tests may also detect changed pybind11 docstring formatting. The Unix Makefile version is unchanged for isolation. The Windows test venv uses pytest 8 and pytest-asyncio 0.24 with auto mode, avoiding the ancient development dependency versions on Python 3.12.
- Official TBB release binary layout and ABI, Stan Math MSVC template compatibility, Sundials build, stanc Windows executable, wheel packaging and actual Windows sampling remain unverified until Actions runs. Pure MSVC may fail. No unsupported Stan Math feature is disabled to force compilation; no MinGW masquerading as MSVC.
- The experiment was created in a Linux environment, not native Windows. Static Python syntax, YAML/TOML parsing, six branch-selection cases, POSIX socket regression with GCC and Clang, simulated Python-side TCP authentication and gzip framing, and patch application were checked locally. No full Stan build or Windows test has run locally. The native toolchain/SDK and project dependencies are absent; full upstream lint/test execution is not claimed.

## Phase 2 (only after confirmation)

Build the double-clickable `httpstan-server.exe` in its own clean Windows job and upload it via `actions/upload-artifact`; a separate Linux runner would build a Linux one-file executable. Test `multiprocessing.freeze_support()` before imports/workers, server health, shutdown, model compilation and sampling. PyInstaller must include the Python runtime, httpstan package metadata, stanc executable, native libraries, service object, model headers and CPython link artifacts needed for runtime compilation. MSVC/SDK are external or separately provisioned according to their license. A clean machine without a C++ toolchain may start the server but cannot compile arbitrary new Stan models using this backend.

PyStan 3.14.0's `stan/common.py::HttpstanClient` currently always launches its own aiohttp app. For the executable, introduce a separate opt-in external-server URL and/or a loopback health/version negotiation, preserve the embedded fallback, and avoid untrusted remote connections. This also means separating PyStan client-only dependencies from the httpstan build requirements if the client is to work without an installed httpstan wheel. Do not implement this until round one has a verified winner.
