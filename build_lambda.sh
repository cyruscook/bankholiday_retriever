#!/bin/sh

set -e
export AWS_PAGER=""

: "${AWS_REGION:?AWS_REGION not set}"
: "${1:?no provided function name}"

docker build -t bankholiday-retriever --provenance=false .

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws ecr get-login-password | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
docker tag bankholiday-retriever:latest "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/bankholiday-retriever:latest"
docker push "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/bankholiday-retriever:latest"

aws lambda update-function-code --function-name $1 --image-uri "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/bankholiday-retriever:latest"
