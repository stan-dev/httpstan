"""Top-level script environment for httpstan.

``python3 -m httpstan`` starts a server listening on ``localhost``.

As httpstan is intended for use alongside a frontend, the frontend
will typically do everything in ``main()`` function.
"""
import time

import httpstan.main


def main():
    host = "127.0.0.1"
    port = 8080
    server = httpstan.main.Server(host=host, port=port)
    server.start()
    try:
        while True:
            time.sleep(0.1)
    finally:
        server.stop()


if __name__ == "__main__":
    main()
