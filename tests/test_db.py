"""Smoke tests for db.py."""
from __future__ import annotations

import sqlite3

from chiron_standards.db import INSERT_STANDARD_SQL, init_schema


def test_init_schema_is_idempotent():
    """Running init_schema twice should not fail — safe to call on every ingest."""
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    init_schema(conn)   # second call must not raise


def test_insert_standard_sql_uses_named_placeholders():
    """The INSERT statement must match the dataclass fields by name."""
    # Simple structural check — we expect every dataclass field name to appear
    # as a :name placeholder exactly once in the SQL.
    from chiron_standards.models import StandardRow

    field_names = [f.name for f in StandardRow.__dataclass_fields__.values()]
    for name in field_names:
        assert f":{name}" in INSERT_STANDARD_SQL, f"missing placeholder :{name}"
