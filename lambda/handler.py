import os
import re
from datetime import datetime, timezone
from urllib.parse import unquote_plus

import boto3

INCOMING_PREFIX = os.environ.get("INCOMING_PREFIX", "incoming/")
PROCESSED_PREFIX = os.environ.get("PROCESSED_PREFIX", "processed/")
IGNORED_PREFIX = os.environ.get("IGNORED_PREFIX", "ignored/")

PATTERNS = {
    ".csv": re.compile(os.environ.get("CSV_PATTERN", r"^report_\d{8}\.csv$")),
    ".json": re.compile(os.environ.get("JSON_PATTERN", r"^data_[a-z0-9]+_v\d+\.json$")),
}

s3 = boto3.client("s3", endpoint_url=os.environ.get("S3_ENDPOINT_URL") or None)


def matches_pattern(filename):
    _, ext = os.path.splitext(filename)
    pattern = PATTERNS.get(ext.lower())
    return bool(pattern and pattern.match(filename))


def add_timestamp(filename, now):
    name, ext = os.path.splitext(filename)
    return f"{name}_{now.strftime('%Y%m%d_%H%M%S')}{ext}"


def move_object(bucket, src_key, dst_key):
    s3.copy_object(Bucket=bucket, Key=dst_key, CopySource={"Bucket": bucket, "Key": src_key})
    s3.delete_object(Bucket=bucket, Key=src_key)


def lambda_handler(event, context):
    results = []

    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])

        # Пропускаємо "папки" та об'єкти поза вхідною папкою
        if not key.startswith(INCOMING_PREFIX) or key.endswith("/"):
            continue

        filename = key[len(INCOMING_PREFIX):]
        if "/" in filename:
            filename = filename.rsplit("/", 1)[1]

        if matches_pattern(filename):
            dst_key = PROCESSED_PREFIX + add_timestamp(filename, datetime.now(timezone.utc))
            status = "processed"
        else:
            dst_key = IGNORED_PREFIX + filename
            status = "ignored"

        move_object(bucket, key, dst_key)
        print(f"{status}: s3://{bucket}/{key} -> s3://{bucket}/{dst_key}")
        results.append({"source": key, "destination": dst_key, "status": status})

    return {"results": results}
