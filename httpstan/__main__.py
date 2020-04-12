"""Top-level script environment for httpstan.

``python3 -m httpstan`` starts a server listening on ``127.0.0.1``.

"""
import argparse

import aiohttp.web

import httpstan.app

parser = argparse.ArgumentParser(description="Launch httpstan HTTP server.")
parser.add_argument("--host", default="127.0.0.1")
parser.add_argument("--port", default="8080")

if __name__ == "__main__":
    args = parser.parse_args()
    app = httpstan.app.make_app()
    aiohttp.web.run_app(app, host=args.host, port=args.port)
