# requirements: boto3

import os
import logging
import boto3
import json
import urllib3
from concurrent.futures import ThreadPoolExecutor
from notice_retriever import get_notice_text
from notice_retriever import fetch_all_notices
from notice_parser import parse_notice


logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO").upper())

# S3 bucket to send list of bank holidays to
S3_BUCKET = os.environ.get("S3_BUCKET")
# SNS Topic for errors
SNS_TOPIC = os.environ.get("SNS_TOPIC")



def process_notice(sns, http: urllib3.PoolManager, notice):
    notice_id = notice["id"]
    logging.debug("Processing notice '%s'", notice_id)
    try:
        text = get_notice_text(http, notice_id)
        bhs, nbhs = parse_notice(text)
        logging.debug("Parsed notice '%s' for result: '%s' '%s'", text, bhs, nbhs)
    except Exception as e:
        logging.exception(
            "Failed to process notice '%s' (%s)",
            notice_id,
            type(e).__name__,
        )
        if SNS_TOPIC:
            try:
                sns.publish(
                    TopicArn=SNS_TOPIC,
                    Message=(
                        f"Failed to process notice {notice_id}: "
                        f"{type(e).__name__}: {e}"
                    ),
                )
            except Exception:
                logging.exception(
                    "Failed to publish processing failure for notice '%s'",
                    notice_id,
                )
        raise

    return notice_id, list(set(bhs)), list(set(nbhs))


def lambda_handler(event, context):
    request_id = getattr(context, "aws_request_id", None)
    logging.info("Starting Lambda invocation (request_id=%s)", request_id)
    try:
        return _lambda_handler(event, context)
    except Exception:
        logging.exception("Lambda invocation failed (request_id=%s)", request_id)
        raise


def _lambda_handler(event, context):
    s3 = boto3.client("s3")
    sns = boto3.client("sns")
    http = urllib3.PoolManager(maxsize=10, block=True)

    bank_holidays = {}
    not_bank_holidays = {}

    with ThreadPoolExecutor(max_workers=5) as executor:
        jobs = []

        def process_item(item):
            notice_id = item["id"]
            jobs.append(
                (
                    notice_id,
                    executor.submit(process_notice, sns, http, item),
                )
            )

        logging.info("Fetching proclamations by the monarch")
        # Fetch proclamations in London Gazette
        fetch_all_notices(
            http,
            "London",
            '"Banking and Financial Dealings Act 1971"',
            process_item,
        )
        logging.info("Fetching proclamations by the Secretary of State")
        # Fetch proclamations published in Belfast Gazette
        fetch_all_notices(
            http,
            "Belfast",
            '"Banking and Financial Dealings Act 1971"',
            process_item,
        )
        logging.info("Fetching proclamations by the monarch in scotland")
        # Fetch proclamations published in Edinburgh Gazette
        fetch_all_notices(
            http,
            "Edinburgh",
            '"Banking and Financial Dealings Act 1971"',
            process_item,
        )

        for submitted_notice_id, job in jobs:
            try:
                notice_id, bhs, nbhs = job.result()
            except Exception:
                logging.exception(
                    "Notice worker failed for '%s'",
                    submitted_notice_id,
                )
                raise
            if bhs:
                if notice_id in bank_holidays:
                    logging.error(
                        "The same notice (%s) was processed twice - previously '%s', now '%s'",
                        notice_id,
                        bank_holidays[notice_id],
                        bhs,
                    )
                    raise Exception("Processed same notice twice")
                bank_holidays[notice_id] = bhs
            if nbhs:
                if notice_id in not_bank_holidays:
                    logging.error(
                        "The same notice (%s) was processed twice - previously '%s', now '%s'",
                        notice_id,
                        not_bank_holidays[notice_id],
                        nbhs,
                    )
                    raise Exception("Processed same notice twice")
                not_bank_holidays[notice_id] = nbhs

    bh_json = json.dumps(bank_holidays, default=str)
    s3.put_object(
        Body=bh_json.encode("utf-8"),
        Bucket=S3_BUCKET,
        Key="proclaimed_bhs.json",
        ContentType="application/json; charset=utf-8",
    )
    logging.info("Uploaded bank holidays to S3")

    nbh_json = json.dumps(not_bank_holidays, default=str)
    s3.put_object(
        Body=nbh_json.encode("utf-8"),
        Bucket=S3_BUCKET,
        Key="proclaimed_not_bhs.json",
        ContentType="application/json; charset=utf-8",
    )
    logging.info("Uploaded no longer bank holidays to S3")

    return {
        "bank_holidays": json.loads(bh_json),
        "not_bank_holidays": json.loads(nbh_json),
    }


if __name__ == "__main__":
    lambda_handler({}, {})
