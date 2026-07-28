# Gazette Bank Holiday Retriever

`uv` Python app which retrieves and parses proclamations of bank holidays made under Section 1 of the Banking and Financial Dealings Act 1971 and published in The London Gazette, The Edinburgh Gazette and The Belfast Gazette.

For each proclamation, the app parses the dates proclaimed as being bank holidays, and dates proclaimed as no longer being bank holidays. These are then published as two objects to an S3 bucket, with keys `proclaimed_bhs.json` and `proclaimed_not_bhs.json`. 

The app is packaged as a Docker image and run on AWS Lambda.

The Lambda should have the following environment variables:
* `LOGLEVEL` - the log level, `INFO` if not specified
* `S3_BUCKET` - the S3 bucket to publish the results to
* `SNS_TOPIC` - an SNS topic to send errors to if a proclamation could not be parsed, will just not send an error if the environment variable doesn't exist

## Key commands

* Formatting: `uvx ruff format`
* Linting/type checking: `uvx ruff check` and `uvx ty check`
* Tests: `uv run pytest`
