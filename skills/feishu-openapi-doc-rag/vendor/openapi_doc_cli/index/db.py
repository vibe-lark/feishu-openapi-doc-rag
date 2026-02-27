from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def fts5_available(conn: sqlite3.Connection) -> bool:
    try:
        opts = [r[0] for r in conn.execute("PRAGMA compile_options;").fetchall()]
        return any("FTS5" in o for o in opts)
    except sqlite3.DatabaseError:
        return False


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS docs (
          id TEXT PRIMARY KEY,
          origin_id TEXT NOT NULL,
          url TEXT NOT NULL UNIQUE,
          directory_json TEXT NOT NULL,
          directory_path TEXT NOT NULL,
          pathnames_json TEXT NOT NULL,
          pathnames_path TEXT NOT NULL,
          original_path TEXT,
          update_time_ms INTEGER NOT NULL,
          content TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS docs_update_time_ms ON docs(update_time_ms);
        CREATE INDEX IF NOT EXISTS docs_directory_path ON docs(directory_path);
        """
    )


def init_fts(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(
          id UNINDEXED,
          directory_path,
          pathnames_path,
          original_path,
          url,
          content
        );
        """
    )
