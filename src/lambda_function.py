# requirements: boto3

import os
import logging
import boto3
import json
import datetime
import urllib3
import threading
from concurrent.futures import ThreadPoolExecutor
from notice_retriever import get_notice_text
from notice_retriever import fetch_all_notices
from notice_parser import parse_notice


logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO").upper())

# S3 bucket to send list of bank holidays to
S3_BUCKET = os.environ.get("S3_BUCKET")
# SNS Topic for errors
SNS_TOPIC = os.environ.get("SNS_TOPIC")

BANK_HOLIDAYS: dict[str, list[datetime.date]] = {}
BANK_HOLIDAYS_LOCK = threading.Lock()
NOT_BANK_HOLIDAYS: dict[str, list[datetime.date]] = {}
NOT_BANK_HOLIDAYS_LOCK = threading.Lock()


def process_notice(sns, http: urllib3.PoolManager, notice):
    notice_id = notice["id"]
    logging.debug("Processing notice '%s'", notice_id)
    try:
        text = get_notice_text(http, notice_id)
        bhs, nbhs = parse_notice(text)
        logging.debug("Parsed notice '%s' for result: '%s' '%s'", text, bhs, nbhs)
    except Exception as e:
        logging.exception("Failed to process notice")
        if SNS_TOPIC:
            sns.publish(
                TopicArn=SNS_TOPIC, Message=f"Failed to process notice {notice_id}"
            )
        raise e

    if bhs:
        with BANK_HOLIDAYS_LOCK:
            if notice_id in BANK_HOLIDAYS:
                logging.error(
                    "The same notice (%s) was processed twice - previously '%s', now '%s'",
                    notice_id,
                    BANK_HOLIDAYS[notice_id],
                    bhs,
                )
                raise Exception("Processed same notice twice")
            BANK_HOLIDAYS[notice_id] = bhs
    if nbhs:
        with NOT_BANK_HOLIDAYS_LOCK:
            if notice_id in NOT_BANK_HOLIDAYS:
                logging.error(
                    "The same notice (%s) was processed twice - previously '%s', now '%s'",
                    notice_id,
                    NOT_BANK_HOLIDAYS[notice_id],
                    nbhs,
                )
                raise Exception("Processed same notice twice")
            NOT_BANK_HOLIDAYS[notice_id] = nbhs


def lambda_handler(event, context):
    s3 = boto3.client("s3")
    sns = boto3.client("sns")
    http = urllib3.PoolManager(maxsize=10, block=True)

    with ThreadPoolExecutor(max_workers=5) as executor:
        jobs = []

        def process_item(item):
            jobs.append(executor.submit(process_notice, sns, http, item))

        logging.info("Fetching proclamations by the monarch")
        # Fetch proclamations for England, Wales, Scotland, and Northern Ireland by the King
        fetch_all_notices(
            http,
            "London",
            '"Banking and Financial Dealings Act 1971" NOT "Secretary of State"',
            process_item,
        )
        logging.info("Fetching proclamations by the Secretary of State")
        # Fetch proclamations for Northern Ireland by the Secretary of State
        fetch_all_notices(
            http,
            "Belfast",
            '"Banking and Financial Dealings Act 1971" AND "Secretary of State"',
            process_item,
        )

        for job in jobs:
            job.result()

    with BANK_HOLIDAYS_LOCK:
        bh_json = json.dumps(BANK_HOLIDAYS, default=str)
        s3.put_object(
            Body=bh_json.encode("utf-8"),
            Bucket=S3_BUCKET,
            Key="proclaimed_bhs.json",
            ContentType="application/json; charset=utf-8",
        )
        logging.info("Uploaded bank holidays to S3")

    with NOT_BANK_HOLIDAYS_LOCK:
        nbh_json = json.dumps(NOT_BANK_HOLIDAYS, default=str)
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
