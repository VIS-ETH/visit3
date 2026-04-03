#!/bin/bash

# protobuf generation for python is stupid
# this is a small script to make it work
set -e

PROTO_PATH=$1
PREFIX=$2

if [ -z "$PROTO_PATH" ]; then
  echo "Usage: $0 <path> <package-prefix>";
  exit 1;
fi

if [ -z "$PREFIX" ]; then
  echo "Usage: $0 <path> <package-prefix>";
  exit 1;
fi

TARGET="$PROTO_PATH"

if [ ! -d "$TARGET" ]; then
  mv "$PROTO_PATH" "${PROTO_PATH}-tmp"
  mkdir -p "$PROTO_PATH"
  mv "${PROTO_PATH}-tmp" "$TARGET"
fi

cd "$TARGET"

for dir in $(find . -mindepth 1 -type d); do
  pkgName="$( echo $dir | perl -pE 's/^\.\///g' | perl -pE 's/\//\./g' )"
  echo "$pkgName -> $PREFIX.$pkgName"
  pkgRegex="$( echo $pkgName | perl -pE 's/\./\\\./g' )"
  find $dir -mindepth 1 -maxdepth 1 -type f -name "*.py*" | xargs perl -pi -E "s/^from ($pkgName)/from $PREFIX.\$1/g"
  find $dir -maxdepth 1 -maxdepth 1 -type f -name "*.py*" | xargs perl -pi -E "s/^import ($pkgName)/import $PREFIX.\$1/g"
  find $dir -maxdepth 1 -maxdepth 1 -type f -name "*.pyi" | xargs perl -pi -E "s/\[($pkgName)\./\[$PREFIX.\$1\./g"
done
