"""Top-level script environment for httpstan.

``python3 -m httpstan`` starts a server listening on ``localhost``.

As httpstan is intended for use alongside a frontend, the frontend
will typically start its own event loop and add this server to that.
"""
import asyncio

import aiohttp.web

import httpstan.main


if __name__ == '__main__':
    host = '127.0.0.1'
    port = 8080
    app = httpstan.main.make_app(loop=asyncio.get_event_loop())
    aiohttp.web.run_app(app, host=host, port=port)
