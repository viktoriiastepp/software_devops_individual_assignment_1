import os
import sqlite3

DB_FILENAME = "padel.db"


def db_path():
    """Full path of the SQLite file inside DATA_DIR (default: ./data). Creates the folder if missing."""
    data_dir = os.environ.get("DATA_DIR", "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, DB_FILENAME)


def get_connection():
    """Open a connection to the SQLite database."""
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row  # lets me read columns by name, e.g. row["name"]
    conn.execute("PRAGMA foreign_keys = ON")  # SQLite only enforces foreign keys when this is switched on
    return conn
