# Gazette Bank Holiday Retriever

Retrieves proclamations of bank holidays under Section 1 of the Banking and Financial Dealings Act 1971 and updates an S3 bucket with the parsed results.
The S3 bucket will contain two files, `proclaimed_bhs.json`, with any dates proclaimed to be a bank holiday, and `proclaimed_not_bhs.json`, with any dates proclaimed not to be a bank holiday.

Can be deployed as an AWS lambda:
1. Create an arm64 python 3.11 lambda function
1. Run `build_lambda.sh {lambda_function_name}`

The lambda should have the following environment variables:
* `LOGLEVEL` - the log level, `INFO` if not specified
* `S3_BUCKET` - the S3 bucket to publish the results to
* `SNS_TOPIC` - an SNS topic to send errors to if a proclamation could not be parsed, will just not send an error if the environment variable doesn't exist
