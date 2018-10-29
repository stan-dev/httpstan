#!/bin/bash
# script to download wheels from latest release
set -euo pipefail
IFS=$'\n\t'

RACKSPACE_URL=http://e326305f4e1314aac7e7-e10edc2115386a16a3806cf0a3ef03f1.r17.cf5.rackcdn.com/
PACKAGE=httpstan
VERSION=$(git tag --sort version:refname | grep -v rc | tail -1 | sed 's/^v//')
WHEEL_HEAD="${PACKAGE}-${VERSION}"
WIN_TAIL32="win32.whl"
WIN_TAIL64="win_amd64.whl"
MANYLINUX1_TAIL32="manylinux1_i686.whl"
MANYLINUX1_TAIL64="manylinux1_x86_64.whl"
MACOS_TAIL64="macosx_10_6_intel.macosx_10_9_intel.macosx_10_9_x86_64.macosx_10_10_intel.macosx_10_10_x86_64.whl"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
mkdir -p "$DIR/../dist"
pushd "$DIR/../dist" > /dev/null
rm -rf *.whl

for py_tag in cp36 cp37; do
  wheel_name="$WHEEL_HEAD-$py_tag-${py_tag}m-$MACOS_TAIL64"
  wheel_url="${RACKSPACE_URL}/${wheel_name}"
  echo "downloading: $wheel_name"
  curl -f -O $wheel_url

  wheel_name="$WHEEL_HEAD-$py_tag-${py_tag}m-$MANYLINUX1_TAIL64"
  wheel_url="${RACKSPACE_URL}/${wheel_name}"
  echo "downloading: $wheel_name"
  curl -f -O $wheel_url
done

# windows only
for py_tag in cp36 cp37; do
  wheel_name="$WHEEL_HEAD-$py_tag-${py_tag}m-$WIN_TAIL32"
  wheel_url="${RACKSPACE_URL}/${wheel_name}"
  echo "downloading: $wheel_name"
  curl -f -O $wheel_url

  wheel_name="$WHEEL_HEAD-$py_tag-${py_tag}m-$WIN_TAIL64"
  wheel_url="${RACKSPACE_URL}/${wheel_name}"
  echo "downloading: $wheel_name"
  curl -f -O $wheel_url
done

popd
echo "wheels have been downloaded into dist/"
