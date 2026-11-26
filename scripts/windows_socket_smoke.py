"""Test the MSVC ABI, SDK and Windows callback transport without Stan headers."""
import argparse
import importlib.util
import secrets
import socket
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "win"
spec = importlib.util.spec_from_file_location("httpstan_windows_build", ROOT / "httpstan/_windows.py")
assert spec and spec.loader
win = importlib.util.module_from_spec(spec)
spec.loader.exec_module(win)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--compiler", choices=["cl", "clang-cl"], required=True)
    args = parser.parse_args()
    source = BUILD / "socket_smoke.cpp"
    source.write_text(
        '#include "unix_socket_client.hpp"\n'
        '#include <string>\n'
        'int main(int argc, char** argv) {\n'
        '  if (argc != 2) return 2;\n'
        '  httpstan::unix_socket_client client(argv[1]);\n'
        '  std::string msg(65536, \'x\');\n'
        '  client.send_line(msg.data(), msg.size());\n'
        '  return 0;\n}\n', encoding="utf-8"
    )
    obj = source.with_suffix(".obj")
    exe = source.with_suffix(".exe")
    win.run([win.compiler(args.compiler), *win.flags(args.compiler), "/I" + str(ROOT / "httpstan"),
             "/showIncludes", "/c", str(source), "/Fo" + str(obj)], BUILD)
    win.run([win.tool("link"), "/NOLOGO", "/MACHINE:X64", "/OUT:" + str(exe), str(obj), "Ws2_32.lib", *win.clang_link_args(args.compiler)], BUILD)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        server.settimeout(20)
        token = secrets.token_hex(32)
        endpoint = f"tcp:{server.getsockname()[1]}:{token}"
        # Never print endpoint: it includes the one-time token.
        with subprocess.Popen([str(exe), endpoint], cwd=BUILD) as process:
            try:
                conn, _ = server.accept()
                with conn:
                    conn.settimeout(20)
                    chunks = []
                    while chunk := conn.recv(4096):
                        chunks.append(chunk)
                assert b"".join(chunks) == token.encode("ascii") + b"\n" + b"x" * 65536 + b"\n"
                assert process.wait(timeout=20) == 0
            finally:
                if process.poll() is None:
                    process.kill()
    print("[socket] PASS: token, 65536-byte payload, newline framing, clean process exit", flush=True)


if __name__ == "__main__":
    main()
