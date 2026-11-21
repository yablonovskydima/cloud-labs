import os
import sys
from pathlib import Path

import boto3
import psycopg

# Same import logic as the Lambda (lambda/importer.py)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lambda"))
from importer import TABLES, import_object  # noqa: E402

BUCKET = os.environ.get("S3_BUCKET", "my-project-bucket")
S3_ENDPOINT = os.environ.get("AWS_ENDPOINT_URL", "http://localhost:4566")
DB_DSN = os.environ.get(
    "DB_DSN",
    "host=localhost port=7001 dbname=opendata user=labadmin password=labpassword",
)

s3 = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "test"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "test"),
)


def main(keys):
    if not keys:
        sys.exit("usage: python scripts/import_from_s3.py <s3 key> [<s3 key> ...]")

    with psycopg.connect(DB_DSN) as conn:
        for key in keys:
            ext = os.path.splitext(key)[1].lower()
            if ext not in TABLES:
                print(f"skip {key}: unsupported extension")
                continue

            body = s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()
            print(f"s3://{BUCKET}/{key}: {import_object(conn, key, ext, body)}")


if __name__ == "__main__":
    main(sys.argv[1:])
