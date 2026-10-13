
import sqlite3

conn = sqlite3.connect("schemaguard.db")

for table in ("schemas", "runs"):
    print(f"\n--- {table.upper()} TABLE ---")

    definition = conn.execute(
        "SELECT sql FROM sqlite_master "
        "WHERE type='table' AND name=?",
        (table,),
    ).fetchone()

    print("Definition:", definition[0] if definition else "Missing")
    print("Columns:")

    for column in conn.execute(f"PRAGMA table_info({table})"):
        print(column)

print("\n--- SCHEMA RECORD COUNT ---")
print(conn.execute("SELECT COUNT(*) FROM schemas").fetchone()[0])

conn.close()
