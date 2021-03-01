import os
import subprocess
import sys
import unittest.mock

sys.path.insert(0, os.path.abspath(".."))
import httpstan

extensions = [
    "autoapi.extension",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinxcontrib.openapi",
    "sphinxcontrib.redoc",
]

redoc = [
    {
        "name": "httpstan API",
        "page": "api",
        "spec": "openapi.yaml",
    },
]

source_suffix = ".rst"
master_doc = "index"
project = "httpstan"
copyright = "2019, httpstan Developers"


intersphinx_mapping = {
    "python": ("http://python.readthedocs.io/en/latest/", None),
}

# use `git describe` because `httpstan.__version__` is not available on readthedocs
version = release = subprocess.check_output(["git", "describe", "--abbrev=0", "--always"]).decode().strip()

autoapi_dirs = [os.path.join("..", "httpstan")]
autoapi_ignore = [
    "*lib*",
    "*views.py",
    "*openapi.py",
]

################################################################################
# openapi spec
################################################################################


def make_openapi_spec(_):
    print("conf.py: Generating openapi spec... ", end="")
    source_dir = os.path.dirname(os.path.realpath(__file__))
    output_path = os.path.join(source_dir, "openapi.yaml")

    # Use mock for extension and generated modules modules so we do not need to
    # build httpstan in order to run Sphinx.
    sys.modules["httpstan.compile"] = unittest.mock.MagicMock()
    sys.modules["httpstan.callbacks_writer_pb2"] = unittest.mock.MagicMock()

    from httpstan import openapi

    with open(output_path, "w") as fh:
        fh.write(openapi.openapi_spec().to_yaml())
    print("done.")


def setup(app):
    app.connect("builder-inited", make_openapi_spec)


################################################################################
# theme configuration
################################################################################

# on_rtd is whether we are on readthedocs.org
on_rtd = os.environ.get("READTHEDOCS", None) == "True"

if not on_rtd:  # only import and set the theme if we're building docs locally
    import sphinx_rtd_theme

    html_theme = "sphinx_rtd_theme"
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
