import hashlib
import json

TABLES = {
    ".csv": "city_routes",
    ".json": "agri_enterprises",
}

AGRI_FIELDS = ["EDRPOU", "Nazva_pidpriemstva", "Adress", "FIO", "KVED"]


def copy_routes_csv(cur, body):
    cur.execute("CALL prepare_city_routes_stage()")
    copy_sql = "COPY stage_city_routes FROM STDIN WITH (FORMAT csv, DELIMITER ';', HEADER true, NULL 'null')"
    with cur.copy(copy_sql) as copy:
        copy.write(body.decode("utf-8-sig"))


def copy_agri_json(cur, body):
    cur.execute("CALL prepare_agri_enterprises_stage()")
    records = json.loads(body.decode("utf-8-sig"))
    copy_sql = "COPY stage_agri_enterprises (edrpou, name, address, director, kved) FROM STDIN"
    with cur.copy(copy_sql) as copy:
        for record in records:
            copy.write_row([None if record.get(f) is None else str(record[f]) for f in AGRI_FIELDS])


LOADERS = {
    "city_routes": copy_routes_csv,
    "agri_enterprises": copy_agri_json,
}


def import_object(conn, source_file, ext, body):
    """Loads one file into its main table. Returns import statistics."""
    table = TABLES[ext]
    digest = hashlib.sha256(body).hexdigest()

    with conn.transaction(), conn.cursor() as cur:
        # The same file content was already imported -> nothing to do
        cur.execute("SELECT source_file FROM import_log WHERE file_sha256 = %s", (digest,))
        previous = cur.fetchone()
        if previous:
            return {"table": table, "status": "duplicate_file", "duplicate_of": previous[0]}

        LOADERS[table](cur, body)
        cur.execute(f"CALL merge_{table}(%s, NULL, NULL, NULL, NULL)", (source_file,))
        rows_in_file, inserted, updated, skipped = cur.fetchone()

        cur.execute(
            """
            INSERT INTO import_log (source_file, file_sha256, target_table, rows_in_file, inserted, updated, skipped)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (file_sha256) DO NOTHING
            """,
            (source_file, digest, table, rows_in_file, inserted, updated, skipped),
        )

    return {
        "table": table,
        "status": "imported",
        "rows_in_file": rows_in_file,
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
    }
