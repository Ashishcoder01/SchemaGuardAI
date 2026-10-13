import os
import json
import sqlite3
from datetime import datetime, timezone

import psycopg


SQLITE_PATH = "schemaguard.db"
POSTGRES_URL = os.environ.get("POSTGRES_MIGRATION_URL", "").strip()

if not POSTGRES_URL:
    raise SystemExit("STOP: PostgreSQL URL is not configured.")

POSTGRES_URL = POSTGRES_URL.replace(
    "postgresql+psycopg://",
    "postgresql://",
    1,
)


def normalize_time(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def normalize_json(value):
    if value is None:
        return None
    if isinstance(value, str):
        return json.loads(value)
    return value


def compare_table(sqlite_conn, pg_conn, table, columns, json_columns=()):
    sqlite_rows = sqlite_conn.execute(
        f"SELECT {', '.join(columns)} FROM {table} ORDER BY id"
    ).fetchall()

    with pg_conn.cursor() as cursor:
        cursor.execute(
            f"SELECT {', '.join(columns)} FROM {table} ORDER BY id"
        )
        pg_rows = cursor.fetchall()

    if len(sqlite_rows) != len(pg_rows):
        raise AssertionError(
            f"{table}: row count differs: "
            f"SQLite={len(sqlite_rows)}, PostgreSQL={len(pg_rows)}"
        )

    for index, (sqlite_row, pg_row) in enumerate(zip(sqlite_rows, pg_rows)):
        for column, old_value, new_value in zip(columns, sqlite_row, pg_row):
            if column == "created_at":
                old_value = normalize_time(old_value)
                new_value = normalize_time(new_value)
            elif column in json_columns:
                old_value = normalize_json(old_value)
                new_value = normalize_json(new_value)

            if old_value != new_value:
                raise AssertionError(
                    f"{table}, row {index}, field '{column}' differs.\n"
                    f"SQLite: {old_value!r}\n"
                    f"PostgreSQL: {new_value!r}"
                )

    print(f"PASS: {table} — {len(sqlite_rows)} rows, all fields match.")


def main():
    sqlite_conn = sqlite3.connect(
        f"file:{SQLITE_PATH}?mode=ro", uri=True
    )
    try:
        if sqlite_conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise AssertionError("SQLite integrity check failed.")

        with psycopg.connect(POSTGRES_URL) as pg_conn:
            compare_table(
                sqlite_conn,
                pg_conn,
                "schemas",
                [
                    "id", "name", "description", "schema_json",
                    "version", "created_at", "active",
                ],
                json_columns=("schema_json",),
            )
            compare_table(
                sqlite_conn,
                pg_conn,
                "runs",
                [
                    "id", "status", "provider", "model", "prompt_preview",
                    "output_json", "errors_json", "attempts", "latency_ms",
                    "created_at", "prompt", "schema_name", "success",
                ],
                json_columns=("output_json", "errors_json"),
            )

        print("\nFULL COMPARISON PASSED.")
        print("SQLite source and backup remain untouched.")
    finally:
        sqlite_conn.close()


if __name__ == "__main__":
    main()
