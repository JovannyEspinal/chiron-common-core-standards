"""SQLite schema + connection helper for the standards database."""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "standards.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS standards (
  id              TEXT PRIMARY KEY,
  notation_short  TEXT,
  notation_full   TEXT,
  description     TEXT NOT NULL,
  grade           TEXT NOT NULL,
  subject         TEXT NOT NULL,
  jurisdiction    TEXT NOT NULL,
  set_id          TEXT NOT NULL,
  depth           INTEGER NOT NULL,
  position        INTEGER NOT NULL,
  parent_id       TEXT,
  ancestor_ids    TEXT,
  statement_label TEXT,
  source_url      TEXT
);

CREATE INDEX IF NOT EXISTS idx_notation_short ON standards(notation_short);
CREATE INDEX IF NOT EXISTS idx_grade_subject  ON standards(grade, subject);
CREATE INDEX IF NOT EXISTS idx_parent         ON standards(parent_id);

CREATE VIRTUAL TABLE IF NOT EXISTS standards_fts USING fts5(
  description,
  ancestor_descriptions,
  content=''
);

CREATE TABLE IF NOT EXISTS standards_vec (
  standard_id TEXT PRIMARY KEY REFERENCES standards(id),
  embedding   BLOB NOT NULL
);
"""

INSERT_STANDARD_SQL = """
INSERT OR REPLACE INTO standards (
    id, notation_short, notation_full, description, grade, subject,
    jurisdiction, set_id, depth, position, parent_id, ancestor_ids,
    statement_label, source_url
) VALUES (
    :id, :notation_short, :notation_full, :description, :grade, :subject,
    :jurisdiction, :set_id, :depth, :position, :parent_id, :ancestor_ids,
    :statement_label, :source_url
)
"""

def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    """Open the DB with sane defaults. Creates parent dir if missing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Create tables/indexes if they don't exist. Idempotent."""
    conn.executescript(SCHEMA)
    conn.commit()
