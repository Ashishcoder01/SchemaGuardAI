
import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "schemaguard.db"


def columns(connection, table_name):
    return {
        row["name"]
        for row in connection.execute(
            f'PRAGMA table_info("{table_name}")'
        ).fetchall()
    }


def migrate():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BASE_DIR / f"schemaguard_backup_{timestamp}.db"

    # Make a consistent backup using SQLite's backup API.
    with sqlite3.connect(DB_PATH) as source:
        with sqlite3.connect(backup_path) as backup:
            source.backup(backup)

    with sqlite3.connect(backup_path) as backup:
        integrity = backup.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if integrity != "ok":
            raise RuntimeError(
                f"Backup integrity check failed: {integrity}"
            )

    print(f"Backup created: {backup_path}")
    print("Backup integrity: OK")

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    try:
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("BEGIN IMMEDIATE")

        run_columns = columns(connection, "runs")
        schema_columns = columns(connection, "schemas")

        required_tables = {"runs", "schemas"}
        existing_tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table'"
            ).fetchall()
        }

        missing_tables = required_tables - existing_tables
        if missing_tables:
            raise RuntimeError(
                f"Required tables are missing: {missing_tables}"
            )

        # Add only missing columns. Existing legacy columns stay intact.
        run_additions = {
            "prompt": "TEXT NOT NULL DEFAULT ''",
            "schema_name": (
                "VARCHAR(150) NOT NULL DEFAULT 'legacy'"
            ),
            "success": "BOOLEAN NOT NULL DEFAULT 0",
        }

        for name, definition in run_additions.items():
            if name not in run_columns:
                connection.execute(
                    f'ALTER TABLE runs ADD COLUMN "{name}" '
                    f"{definition}"
                )
                print(f"Added runs.{name}")

        if "active" not in schema_columns:
            connection.execute(
                "ALTER TABLE schemas ADD COLUMN "
                "active BOOLEAN NOT NULL DEFAULT 1"
            )
            print("Added schemas.active")

        # Preserve prompt_preview and backfill the new prompt field.
        if "prompt_preview" in run_columns:
            connection.execute(
                """
                UPDATE runs
                SET prompt = COALESCE(prompt_preview, '')
                WHERE prompt IS NULL OR prompt = ''
                """
            )

        # Preserve status and map its values to the new boolean field.
        if "status" in run_columns:
            connection.execute(
                """
                UPDATE runs
                SET success = CASE
                    WHEN lower(trim(COALESCE(status, '')))
                         IN ('success', 'true', '1')
                    THEN 1
                    ELSE 0
                END
                """
            )

        # Do not assume the legacy "model" column is a schema name.
        # Keep its original values and mark unmapped names as legacy.
        connection.execute(
            """
            UPDATE runs
            SET schema_name = 'legacy'
            WHERE schema_name IS NULL OR schema_name = ''
            """
        )

        connection.commit()

        # Verify the migrated tables and record counts.
        run_columns = columns(connection, "runs")
        schema_columns = columns(connection, "schemas")

        required_run_columns = {
            "id", "prompt", "provider", "schema_name",
            "success", "attempts", "latency_ms",
            "output_json", "errors_json", "created_at",
        }
        required_schema_columns = {
            "id", "name", "version", "schema_json",
            "active", "created_at",
        }

        if not required_run_columns.issubset(run_columns):
            raise RuntimeError(
                "Migration verification failed for runs."
            )

        if not required_schema_columns.issubset(schema_columns):
            raise RuntimeError(
                "Migration verification failed for schemas."
            )

        run_count = connection.execute(
            "SELECT COUNT(*) FROM runs"
        ).fetchone()[0]

        schema_count = connection.execute(
            "SELECT COUNT(*) FROM schemas"
        ).fetchone()[0]

        success_count = connection.execute(
            "SELECT COUNT(*) FROM runs WHERE success = 1"
        ).fetchone()[0]

        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if integrity != "ok":
            raise RuntimeError(
                f"Database integrity check failed: {integrity}"
            )

        print("\nMigration completed.")
        print(f"Database: {DB_PATH}")
        print(f"Run records preserved: {run_count}")
        print(f"Schema records preserved: {schema_count}")
        print(f"Successful runs: {success_count}")
        print(f"Database integrity: {integrity}")
        print("Legacy columns and values have been retained.")

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    migrate()
