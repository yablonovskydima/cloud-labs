import os
import sys

import boto3
import psycopg

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


def import_routes_csv(cur, key, body):
    cur.execute("""
        CREATE TEMP TABLE routes_stage (
            uid text, agency_id text, short_name text, full_name text, description text,
            type text, homepage text, colour text, text_colour text, sort_order text
        ) ON COMMIT DROP
    """)
    copy_sql = "COPY routes_stage FROM STDIN WITH (FORMAT csv, DELIMITER ';', HEADER true, NULL 'null')"
    with cur.copy(copy_sql) as copy:
        copy.write(body.decode("utf-8-sig"))

    cur.execute("DELETE FROM city_routes WHERE source_file = %s", (key,))
    cur.execute("""
        INSERT INTO city_routes (route_uid, agency_id, short_name, full_name, description,
                                 route_type, homepage, colour, text_colour, sort_order, source_file)
        SELECT trim(uid)::int, trim(agency_id), trim(short_name), trim(full_name),
               nullif(trim(description), ''), trim(type)::smallint, nullif(trim(homepage), ''),
               nullif(trim(colour), ''), nullif(trim(text_colour), ''),
               nullif(trim(sort_order), '')::int, %s
        FROM routes_stage
    """, (key,))
    return cur.rowcount


def import_agri_json(cur, key, body):
    cur.execute("DELETE FROM agri_enterprises WHERE source_file = %s", (key,))
    cur.execute("""
        INSERT INTO agri_enterprises (edrpou, name, address, director, kved, source_file)
        SELECT lpad(x."EDRPOU"::text, 8, '0'), trim(x."Nazva_pidpriemstva"),
               nullif(trim(x."Adress"), ''), nullif(trim(x."FIO"), ''),
               nullif(trim(x."KVED"), ''), %s
        FROM jsonb_to_recordset(%s::jsonb) AS x(
            "EDRPOU" bigint, "Nazva_pidpriemstva" text, "Adress" text, "FIO" text, "KVED" text
        )
    """, (key, body.decode("utf-8-sig")))
    return cur.rowcount


IMPORTERS = {
    ".csv": ("city_routes", import_routes_csv),
    ".json": ("agri_enterprises", import_agri_json),
}


def main(keys):
    if not keys:
        sys.exit(__doc__)

    with psycopg.connect(DB_DSN) as conn:
        for key in keys:
            ext = os.path.splitext(key)[1].lower()
            if ext not in IMPORTERS:
                print(f"skip {key}: unsupported extension")
                continue

            table, importer = IMPORTERS[ext]
            body = s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()
            with conn.transaction(), conn.cursor() as cur:
                count = importer(cur, key, body)
            print(f"s3://{BUCKET}/{key} -> {table}: {count} rows")


if __name__ == "__main__":
    main(sys.argv[1:])
