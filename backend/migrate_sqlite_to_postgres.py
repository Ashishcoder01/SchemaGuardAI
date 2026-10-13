
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, inspect, select, func
from sqlalchemy.orm import Session

from app.database import Base
from app.models import SchemaRecord, RunRecord


SOURCE_DB = Path(__file__).resolve().parent / "schemaguard.db"


def parse_json(value, field_name):
    """Convert SQLite JSON text into a Python value."""
    if value is None:
        return None

    if not isinstance(value, str):
        return value

    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in SQLite field {field_name}: {exc}"
        ) from exc


def parse_datetime(value):
    """Convert SQLite timestamps into Python datetime objects."""
    if isinstance(value, datetime):
        return value

    if not value:
        raise ValueError("Encountered a missing created_at timestamp.")

    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def read_sqlite_records(database_path):
    """Read SQLite data without modifying the source database."""
    if not database_path.exists():
        raise FileNotFoundError(
            f"SQLite database not found: {database_path}"
        )

    uri = f"{database_path.resolve().as_uri()}?mode=ro"

    with sqlite3.connect(uri, uri=True) as connection:
        connection.row_factory = sqlite3.Row

        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if integrity != "ok":
            raise RuntimeError(
                f"SQLite integrity check failed: {integrity}"
            )

        schemas = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM schemas ORDER BY id"
            )
        ]

        runs = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM runs ORDER BY id"
            )
        ]

    return schemas, runs


def main():
    database_url = os.environ.get("POSTGRES_MIGRATION_URL", "").strip()
    
    from urllib.parse import urlsplit

    print("URL supplied:", bool(database_url))
    print("URL starts with postgresql://:", database_url.startswith("postgresql://"))
    print("URL starts with postgres://:", database_url.startswith("postgres://"))
    print("URL starts with postgresql+psycopg://:", database_url.startswith("postgresql+psycopg://"))
    print("URL has surrounding whitespace:", database_url != database_url.strip())
    print("URL contains masking characters:", "*" in database_url)


    if not database_url:
        raise SystemExit(
            "STOP: Set POSTGRES_MIGRATION_URL to your PostgreSQL URL first."
        )

    if database_url.startswith("postgres://"):
        database_url = database_url.replace(
            "postgres://",
            "postgresql+psycopg://",
            1,
        )
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1,
        )

    database_url = database_url.strip()

    if not database_url.startswith("postgresql+psycopg://"):
        raise SystemExit(
            "STOP: Expected a PostgreSQL URL using the psycopg driver."
        )

    schemas, runs = read_sqlite_records(SOURCE_DB)

    print(f"SQLite source: {SOURCE_DB}")
    print(f"Source schemas: {len(schemas)}")
    print(f"Source runs: {len(runs)}")

    target_engine = create_engine(
        database_url,
        pool_pre_ping=True,
    )

    try:
        with target_engine.connect() as connection:
            if connection.dialect.name != "postgresql":
                raise RuntimeError(
                    "Migration target is not PostgreSQL."
                )

        inspector = inspect(target_engine)
        existing_tables = set(inspector.get_table_names())

        if {"schemas", "runs"}.issubset(existing_tables):
            with Session(target_engine) as session:
                schema_count = session.scalar(
                    select(func.count()).select_from(SchemaRecord)
                )
                run_count = session.scalar(
                    select(func.count()).select_from(RunRecord)
                )

                if schema_count or run_count:
                    raise RuntimeError(
                        "STOP: Target already contains records. "
                        "No records were inserted or overwritten."
                    )

        Base.metadata.create_all(target_engine)

        schema_objects = []
        for row in schemas:
            schema_objects.append(
                SchemaRecord(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    schema_json=parse_json(
                        row["schema_json"], "schemas.schema_json"
                    ),
                    version=row["version"],
                    created_at=parse_datetime(row["created_at"]),
                    active=bool(row["active"]),
                )
            )

        run_objects = []
        for row in runs:
            run_objects.append(
                RunRecord(
                    id=row["id"],
                    status=row["status"],
                    model=row["model"],
                    prompt_preview=row["prompt_preview"],
                    prompt=row["prompt"],
                    provider=row["provider"],
                    schema_name=row["schema_name"],
                    success=bool(row["success"]),
                    attempts=row["attempts"],
                    latency_ms=row["latency_ms"],
                    output_json=parse_json(
                        row["output_json"], "runs.output_json"
                    ),
                    errors_json=parse_json(
                        row["errors_json"], "runs.errors_json"
                    ),
                    created_at=parse_datetime(row["created_at"]),
                )
            )

        with Session(target_engine) as session:
            session.add_all(schema_objects)
            session.add_all(run_objects)
            session.commit()

        with Session(target_engine) as session:
            migrated_schemas = session.scalars(
                select(SchemaRecord.id).order_by(SchemaRecord.id)
            ).all()

            migrated_runs = session.scalars(
                select(RunRecord.id).order_by(RunRecord.id)
            ).all()

        expected_schema_ids = sorted(row["id"] for row in schemas)
        expected_run_ids = sorted(row["id"] for row in runs)

        if migrated_schemas != expected_schema_ids:
            raise RuntimeError(
                "Schema ID verification failed after migration."
            )

        if migrated_runs != expected_run_ids:
            raise RuntimeError(
                "Run ID verification failed after migration."
            )

        print("\nMigration and ID verification succeeded.")
        print(f"Verified schemas: {len(migrated_schemas)}")
        print(f"Verified runs: {len(migrated_runs)}")
        print("Original SQLite database was not modified.")

    finally:
        target_engine.dispose()


if __name__ == "__main__":
    main()
