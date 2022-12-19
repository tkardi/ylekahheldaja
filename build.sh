#!/bin/bash
p_CURDIR=${PWD}

rm -rf ./build || true
mkdir ./build

cp -r ./src/main ./build/main
cp -r ./docker/** ./build

cd build

docker build --tag localhost/ylekahheldus -f Dockerfile .

cd $p_CURDIR
