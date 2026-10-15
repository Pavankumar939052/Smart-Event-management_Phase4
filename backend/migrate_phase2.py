
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "smart_event.db"


def add_column_if_missing(cursor, table, column, definition):
    columns = {
        row[1]
        for row in cursor.execute(f"PRAGMA table_info({table})")
    }

    if column not in columns:
        cursor.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )
        print(f"Added: {table}.{column}")
    else:
        print(f"Already exists: {table}.{column}")


def main():
    connection = sqlite3.connect(DB_PATH)

    try:
        cursor = connection.cursor()

        add_column_if_missing(
            cursor, "users", "role",
            "VARCHAR(20) NOT NULL DEFAULT 'USER'"
        )

        add_column_if_missing(
            cursor, "events", "organizer_id",
            "INTEGER REFERENCES users(id)"
        )

        add_column_if_missing(
            cursor, "events", "event_status",
            "VARCHAR(20) NOT NULL DEFAULT 'UPCOMING'"
        )

        add_column_if_missing(
            cursor, "events", "event_end_date",
            "DATETIME"
        )

        connection.commit()
        print("\nMigration completed successfully.")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    main()
