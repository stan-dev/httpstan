import os
import sys
import unittest.mock

sys.path.insert(0, os.path.abspath(".."))
import httpstan

# Use mock for extension and generated modules modules so we do not need to
# build httpstan in order to run Sphinx.
sys.modules["httpstan.stan"] = unittest.mock.MagicMock()
sys.modules["httpstan.compile"] = unittest.mock.MagicMock()
sys.modules["httpstan.callbacks_writer_pb2"] = unittest.mock.MagicMock()

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinxcontrib.openapi",
    "sphinxcontrib.redoc",
]

redoc = [
    {"name": "httpstan API", "page": "api", "spec": "openapi.yaml",},
]

source_suffix = ".rst"
master_doc = "index"
project = u"httpstan"
copyright = u"2019, httpstan Developers"


intersphinx_mapping = {
    "python": ("http://python.readthedocs.io/en/latest/", None),
}

version = release = httpstan.__version__

################################################################################
# apidoc and openapi spec
################################################################################

# the following "hook" arranges for the equivalent of the following to be run:
# sphinx-apidoc --ext-autodoc --force --no-toc -o doc/source httpstan httpstan/views.py httpstan/routes.py


def run_apidoc(_):

    output_path = source_dir = os.path.dirname(os.path.realpath(__file__))
    # excluding ``httpstan/views.py`` as Sphinx cannot process the OpenAPI YAML
    # excluding ``httpstan/routes.py`` as useless without ``views.py``
    ignored_files = [
        os.path.join(source_dir, "..", "setup.py"),
        os.path.join(source_dir, "..", "httpstan", "views.py"),
        os.path.join(source_dir, "..", "httpstan", "routes.py"),
    ]
    argv = [
        "--ext-autodoc",
        "--force",
        "--no-toc",
        "-o",
        output_path,
        os.path.join(source_dir, "..", project.lower()),
    ] + ignored_files

    from sphinx.ext import apidoc

    apidoc.main(argv)


def make_openapi_spec(_):
    print("conf.py: Generating openapi spec... ", end="")
    source_dir = os.path.dirname(os.path.realpath(__file__))
    output_path = os.path.join(source_dir, "openapi.yaml")
    from httpstan import openapi

    with open(output_path, "w") as fh:
        fh.write(openapi.openapi_spec().to_yaml())
    print("done.")


def setup(app):
    app.connect("builder-inited", run_apidoc)
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
