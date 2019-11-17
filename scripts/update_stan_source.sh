#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

err() {
    echo "$@" >&2
}

if [[ $# -ne 1 ]] ; then
    err "Provide upstream Stan tag (e.g., 'v2.18.1')"
    exit 1
fi

TAG="$1"
VERSION=${TAG//v/}
echo "Updating Stan source to tag: ${TAG}"
read -r -p "Ok to continue (y/n)? " answer
case ${answer:0:1} in
    y|Y )
        echo "Continuing..."
    ;;
    * )
        err "Not updating Stan source"
        exit 1
    ;;
esac

TEMPDIR=$(mktemp -d)
echo "in script proper"
curl -L "https://github.com/stan-dev/stan/archive/${TAG}.tar.gz" | \
    tar -C "${TEMPDIR}" -zxvf -
curl -L "https://github.com/stan-dev/math/archive/${TAG}.tar.gz" | \
    tar -C "${TEMPDIR}" -zxvf -

echo "using temporary directory: ${TEMPDIR}"

pushd "${TEMPDIR}"
rmdir "stan-${VERSION}/lib/stan_math"
mv "${TEMPDIR}/math-${VERSION}" "${TEMPDIR}/stan-${VERSION}/lib/stan_math"
popd


echo "Running 'git stash'"
git stash
rm -rf httpstan/lib/stan
mv "${TEMPDIR}/stan-${VERSION}" httpstan/lib/stan

echo "Running 'git add httpstan/lib/stan -f'"
git add httpstan/lib/stan -f
echo "Running 'git commit' with message:"\
    "'chore: Update Stan source to tag ${TAG}'"
git commit -m"chore: Update Stan source to tag ${TAG}"
