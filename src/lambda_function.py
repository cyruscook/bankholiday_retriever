# requirements: boto3

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor

import boto3
import urllib3

from notice_parser import parse_notice
from notice_retriever import fetch_all_notices, get_notice_text

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO").upper())

LOGGER = logging.getLogger(__name__)

# S3 bucket to send list of bank holidays to
S3_BUCKET = os.environ.get("S3_BUCKET")
# SNS Topic for errors
SNS_TOPIC = os.environ.get("SNS_TOPIC")


class DuplicateNoticeError(Exception):
    """Raised when a notice produces duplicate bank-holiday results."""


def process_notice(sns, http: urllib3.PoolManager, notice):
    notice_id = notice["id"]
    LOGGER.debug("Processing notice '%s'", notice_id)
    try:
        text = get_notice_text(http, notice_id)
        bhs, nbhs = parse_notice(text)
        LOGGER.debug("Parsed notice '%s' for result: '%s' '%s'", text, bhs, nbhs)
    except Exception as e:
        LOGGER.exception(
            "Failed to process notice '%s' (%s)",
            notice_id,
            type(e).__name__,
        )
        if SNS_TOPIC:
            try:
                sns.publish(
                    TopicArn=SNS_TOPIC,
                    Message=(
                        f"Failed to process notice {notice_id}: {type(e).__name__}: {e}"
                    ),
                )
            except Exception:
                LOGGER.exception(
                    "Failed to publish processing failure for notice '%s'",
                    notice_id,
                )
        raise

    return notice_id, list(set(bhs)), list(set(nbhs))


def lambda_handler(event, context):
    request_id = getattr(context, "aws_request_id", None)
    LOGGER.info("Starting Lambda invocation (request_id=%s)", request_id)
    try:
        return _lambda_handler(event, context)
    except Exception:
        LOGGER.exception("Lambda invocation failed (request_id=%s)", request_id)
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

        LOGGER.info("Fetching proclamations by the monarch")
        # Fetch proclamations in London Gazette
        fetch_all_notices(
            http,
            "London",
            '"Banking and Financial Dealings Act 1971"',
            process_item,
        )
        LOGGER.info("Fetching proclamations by the Secretary of State")
        # Fetch proclamations published in Belfast Gazette
        fetch_all_notices(
            http,
            "Belfast",
            '"Banking and Financial Dealings Act 1971"',
            process_item,
        )
        LOGGER.info("Fetching proclamations by the monarch in scotland")
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
                LOGGER.exception(
                    "Notice worker failed for '%s'",
                    submitted_notice_id,
                )
                raise
            if bhs:
                if notice_id in bank_holidays:
                    LOGGER.error(
                        "The same notice (%s) was processed twice - previously '%s', now '%s'",
                        notice_id,
                        bank_holidays[notice_id],
                        bhs,
                    )
                    raise DuplicateNoticeError("Processed same notice twice")
                bank_holidays[notice_id] = bhs
            if nbhs:
                if notice_id in not_bank_holidays:
                    LOGGER.error(
                        "The same notice (%s) was processed twice - previously '%s', now '%s'",
                        notice_id,
                        not_bank_holidays[notice_id],
                        nbhs,
                    )
                    raise DuplicateNoticeError("Processed same notice twice")
                not_bank_holidays[notice_id] = nbhs

    bh_json = json.dumps(bank_holidays, default=str)
    s3.put_object(
        Body=bh_json.encode("utf-8"),
        Bucket=S3_BUCKET,
        Key="proclaimed_bhs.json",
        ContentType="application/json; charset=utf-8",
    )
    LOGGER.info("Uploaded bank holidays to S3")

    nbh_json = json.dumps(not_bank_holidays, default=str)
    s3.put_object(
        Body=nbh_json.encode("utf-8"),
        Bucket=S3_BUCKET,
        Key="proclaimed_not_bhs.json",
        ContentType="application/json; charset=utf-8",
    )
    LOGGER.info("Uploaded no longer bank holidays to S3")

    return {
        "bank_holidays": json.loads(bh_json),
        "not_bank_holidays": json.loads(nbh_json),
    }


if __name__ == "__main__":
    lambda_handler({}, {})
