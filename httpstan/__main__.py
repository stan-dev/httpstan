"""Top-level script environment for httpstan.

``python3 -m httpstan`` starts a server listening on ``localhost``.

"""
import sys
import time

import httpstan.main


def main() -> None:
    server = httpstan.main.Server()
    server.start()
    print(f"httpstan serving on {server.host}:{server.port}", file=sys.stderr)
    try:
        while True:
            time.sleep(0.1)
    finally:
        server.stop()


if __name__ == "__main__":
    main()
