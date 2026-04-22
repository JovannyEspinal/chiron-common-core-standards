"""FastMCP server exposing Common Core standards lookup tools."""
from __future__ import annotations

from dotenv import load_dotenv
from fastmcp import FastMCP

from chiron_standards.db import connect
from chiron_standards.queries import get_standard as _get_standard
from chiron_standards.queries import list_standards as _list_standards
from chiron_standards.queries import search_standards as _search_standards

load_dotenv()
mcp = FastMCP("chiron-standards")
_conn = connect()


@mcp.tool()
def get_standard(code_or_id: str) -> dict | None:
    """Look up a Common Core standard by short notation or GUID.

    Args:
        code_or_id: Either a short notation like 'RL.3.1' or a 32-char GUID.
    """
    return _get_standard(_conn, code_or_id)


@mcp.tool()
def list_standards(
    jurisdiction: str = "Common Core State Standards",
    grade: str | None = None,
    subject: str | None = None,
) -> list[dict]:
    """List all standards matching the given filters, ordered by position.

    Args:
        jurisdiction: Usually 'Common Core State Standards' (the default).
        grade: Two-digit grade string like '02', '03', or '04'. Omit for all grades.
        subject: 'ELA' or 'Math'. Omit for all subjects.
    """
    return _list_standards(
        _conn, jurisdiction=jurisdiction, grade=grade, subject=subject
    )


@mcp.tool()
def search_standards(
    query: str,
    grade: str | None = None,
    subject: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Hybrid FTS5 + semantic search over Common Core standards.

    Use this when you know the concept but not the exact notation.
    Returns leaf standards only (no anchors or parent containers).

    Args:
        query: Natural-language description of the skill or concept.
        grade: Two-digit grade string like '03'. Omit to search across grades.
        subject: 'ELA' or 'Math'. Omit for all subjects.
        limit: Max number of results to return (default 10).
    """
    return _search_standards(
        _conn, query=query, grade=grade, subject=subject, limit=limit
    )

def main():
    mcp.run()

if __name__ == "__main__":
    main()
