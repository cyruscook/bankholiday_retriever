# Gazette Bank Holiday Retriever

Retrieves proclamations of bank holidays under Section 1 of the Banking and Financial Dealings Act 1971 and updates an S3 bucket with the parsed results.
The S3 bucket will contain two files, `proclaimed_bhs.json`, with any dates proclaimed to be a bank holiday, and `proclaimed_not_bhs.json`, with any dates proclaimed not to be a bank holiday.

Can be deployed as an AWS lambda:
1. Mirror the [GHCR image](https://github.com/cyruscook/bankholiday_retriever/pkgs/container/bankholiday_retriever) into ECR
1. Use the Terraform module in [terraform](./terraform/)

## Use the published dataset

I maintain a copy of this Lambda which creates a public free to use dataset of bank holidays at these URLs:
- https://d7rpp5pzwp0ap.cloudfront.net/proclaimed_bhs.json
- https://d7rpp5pzwp0ap.cloudfront.net/proclaimed_not_bhs.json

## FOI Working Day Calculator

This project and its dataset powers the [FOI Working Day Calculator](https://cyruscook.github.io/FOIWorkingDayCalculator)

## Tests

```sh
uvx ruff check && uvx ty check && uv run pytest
```
