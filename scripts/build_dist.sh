#!/bin/bash
# bash strict mode
set -euo pipefail
IFS=$'\n\t'

err() {
  echo "$@" >&2
}

LAST=$(git tag --sort version:refname | grep -v rc | tail -1)

echo "Building distribution for: $LAST"
git checkout "$LAST"

read -r -p "Ok to continue (y/n)? " answer
case ${answer:0:1} in
    y|Y )
        echo "Building distribution"
        python setup.py clean
        python setup.py build_ext --inplace
        python setup.py sdist --formats=gztar
    ;;
    * )
        echo "Not building distribution"
    ;;
esac
