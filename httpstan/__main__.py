"""Top-level script environment for httpstan.

``python3 -m httpstan`` starts a server listening on ``localhost``.

As httpstan is intended for use alongside a frontend, the frontend
will typically do everything in ``main()`` function.
"""
import sys
import time

import httpstan.main


def main():
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
