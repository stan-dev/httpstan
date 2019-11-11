import os
import sys

sys.path.insert(0, os.path.abspath('../..'))
import httpstan

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinxcontrib.openapi',
    'sphinxcontrib.redoc',
]

redoc = [
    {
        'name': 'httpstan API',
        'page': 'api',
        'spec': 'openapi.yaml',
    },
]

source_suffix = '.rst'
master_doc = 'index'
project = u'httpstan'
copyright = u'2019, httpstan Developers'


intersphinx_mapping = {
    "python": ("http://python.readthedocs.io/en/latest/", None),
}

version = release = httpstan.__version__

# on_rtd is whether we are on readthedocs.org
on_rtd = os.environ.get("READTHEDOCS", None) == "True"

if not on_rtd:  # only import and set the theme if we're building docs locally
    import sphinx_rtd_theme

    html_theme = "sphinx_rtd_theme"
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
