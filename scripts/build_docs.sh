#!/bin/bash
# bash strict mode
set -euo pipefail
IFS=$'\n\t'

OPENAPI_FILENAME=doc/source/openapi.yaml
echo "writing OpenAPI spec to $OPENAPI_FILENAME"
python3 -c'from httpstan import openapi; print(openapi.openapi_spec().to_yaml())' > "$OPENAPI_FILENAME"

echo "Generating package API documentation with sphinx-apidoc"
# echo excluding ``httpstan/views.py`` as Sphinx cannot process the the OpenAPI YAML 
# echo excluding ``httpstan/routes.py`` as useless without ``views.py``
sphinx-apidoc --ext-autodoc --force --no-toc -o doc/source httpstan httpstan/views.py httpstan/routes.py

python3 setup.py build_sphinx
