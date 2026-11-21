import os
import re
from datetime import datetime, timezone
from urllib.parse import unquote_plus

import boto3
import psycopg

from importer import import_object

INCOMING_PREFIX = os.environ.get("INCOMING_PREFIX", "incoming/")
PROCESSED_PREFIX = os.environ.get("PROCESSED_PREFIX", "processed/")
IGNORED_PREFIX = os.environ.get("IGNORED_PREFIX", "ignored/")
FAILED_PREFIX = os.environ.get("FAILED_PREFIX", "failed/")

PATTERNS = {
    ".csv": re.compile(os.environ.get("CSV_PATTERN", r"^city_routes_\d{8}\.csv$")),
    ".json": re.compile(os.environ.get("JSON_PATTERN", r"^agri_enterprises_\d{8}\.json$")),
}

DB_CONNINFO = (
    f"host={os.environ.get('DB_HOST', 'localhost')} "
    f"port={os.environ.get('DB_PORT', '5432')} "
    f"dbname={os.environ.get('DB_NAME', 'opendata')} "
    f"user={os.environ.get('DB_USER', 'labadmin')} "
    f"password={os.environ.get('DB_PASSWORD', '')} "
    "connect_timeout=10"
)

s3 = boto3.client("s3", endpoint_url=os.environ.get("S3_ENDPOINT_URL") or None)

# Reused between invocations while the Lambda container is warm
_conn = None


def get_connection():
    global _conn
    if _conn is None or _conn.closed:
        _conn = psycopg.connect(DB_CONNINFO)
    return _conn


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

        if not key.startswith(INCOMING_PREFIX) or key.endswith("/"):
            continue

        filename = key[len(INCOMING_PREFIX):]
        if "/" in filename:
            filename = filename.rsplit("/", 1)[1]

        result = {"source": key}

        # A repeated event for a file that was already moved
        try:
            s3.head_object(Bucket=bucket, Key=key)
        except s3.exceptions.ClientError:
            print(f"skip s3://{bucket}/{key}: object no longer exists")
            continue

        if not matches_pattern(filename):
            dst_key = IGNORED_PREFIX + filename
            result["status"] = "ignored"
        else:
            dst_key = PROCESSED_PREFIX + add_timestamp(filename, datetime.now(timezone.utc))
            try:
                body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
                ext = os.path.splitext(filename)[1].lower()
                result.update(import_object(get_connection(), dst_key, ext, body))
            except Exception as exc:
                print(f"import failed for s3://{bucket}/{key}: {exc!r}")
                dst_key = FAILED_PREFIX + filename
                result.update(status="failed", error=str(exc))

        move_object(bucket, key, dst_key)
        result["destination"] = dst_key
        print(result)
        results.append(result)

    return {"results": results}
