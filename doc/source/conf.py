import os
import sys

sys.path.insert(0, os.path.abspath("../.."))
import httpstan

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

    output_path = os.path.join("doc", "source")
    # excluding ``httpstan/views.py`` as Sphinx cannot process the OpenAPI YAML
    # excluding ``httpstan/routes.py`` as useless without ``views.py``
    ignored_files = [
        "setup.py",
        "httpstan/views.py",
        "httpstan/routes.py",
    ]
    argv = [
        "--ext-autodoc",
        "--force",
        "--no-toc",
        "-o",
        output_path,
        os.path.join("..", project.lower()),
    ] + ignored_files

    from sphinx.ext import apidoc

    apidoc.main(argv)


def make_openapi_spec(_):

    output_path = os.path.join("doc", "source", "openapi.yaml")
    from httpstan import openapi

    with open(output_path, "w") as fh:
        fh.write(openapi.openapi_spec().to_yaml())


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
