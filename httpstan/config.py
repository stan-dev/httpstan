import os

HTTPSTAN_DEBUG = os.environ.get("HTTPSTAN_DEBUG", "0") in {"true", "1"}
