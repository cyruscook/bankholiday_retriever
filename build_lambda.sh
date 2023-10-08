#!/bin/sh

mkdir -p py_deps
pip install --platform manylinux2014_aarch64 --implementation cp --python-version 3.11 --only-binary=:all: --upgrade --target ./py_deps boto3 lxml beautifulsoup4

cd py_deps
zip -r ../lambda.zip .
cd ..
rm -rf py_deps

cd src
zip ../lambda.zip ./*.py
cd ..

aws lambda update-function-code --function-name $1 --zip-file fileb://lambda.zip

rm -f lambda.zip
