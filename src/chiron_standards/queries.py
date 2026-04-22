"""Query functions: lookups, list, hybrid search."""
from __future__ import annotations

import sqlite3
from typing import Any

import numpy as np

from chiron_standards.embeddings import embed_texts


# --- Public API ----------------------------------------------------------

def get_standard(conn: sqlite3.Connection, code_or_id: str) -> dict[str, Any] | None:
    """Look up a single standard by short notation (e.g. 'RL.3.1') or GUID."""
    is_guid = len(code_or_id) == 32 and code_or_id.isalnum()
    column = "id" if is_guid else "notation_short"

    row = conn.execute(
        f"SELECT * FROM standards WHERE {column} = ?",
        (code_or_id,),
    ).fetchone()

    return _row_to_dict(row) if row else None


def list_standards(
    conn: sqlite3.Connection,
    jurisdiction: str = "Common Core State Standards",
    grade: str | None = None,
    subject: str | None = None,
) -> list[dict[str, Any]]:
    """Return all standards matching the given filters, ordered by position."""
    clauses = ["jurisdiction = ?"]
    params: list[Any] = [jurisdiction]

    if grade is not None:
        clauses.append("grade = ?")
        params.append(grade)

    if subject is not None:
        clauses.append("subject = ?")
        params.append(subject)

    where = " AND ".join(clauses)
    rows = conn.execute(
        f"SELECT * FROM standards WHERE {where} ORDER BY position",
        params,
    ).fetchall()

    return [_row_to_dict(r) for r in rows]


def search_standards(
    conn: sqlite3.Connection,
    query: str,
    grade: str | None = None,
    subject: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Hybrid search: FTS5 keyword + vector semantic, merged via RRF."""
    filter_sql, filter_params = _build_filter(grade=grade, subject=subject)

    fts_ranks = _fts_search(conn, query, filter_sql, filter_params)
    vec_ranks = _vector_search(conn, query, filter_sql, filter_params)

    top_scored = _rrf_merge(fts_ranks, vec_ranks, limit=limit)
    return _fetch_rows_preserving_order(conn, top_scored)


# --- Internals ----------------------------------------------------------

_FTS_CANDIDATES = 50
_VEC_CANDIDATES = 50
_RRF_K = 60  # smoothing constant from the original RRF paper


def _build_filter(
    *, grade: str | None, subject: str | None
) -> tuple[str, list[Any]]:
    """Build a shared WHERE fragment + params. Excludes parents and anchors."""
    clauses: list[str] = [
        "s.depth >= 2",
        "(s.notation_short IS NULL OR s.notation_short NOT LIKE 'CCR.%')",
    ]
    params: list[Any] = []
    if grade is not None:
        clauses.append("s.grade = ?")
        params.append(grade)
    if subject is not None:
        clauses.append("s.subject = ?")
        params.append(subject)
    return (" AND ".join(clauses), params)


def _fts_search(
    conn: sqlite3.Connection,
    query: str,
    filter_sql: str,
    filter_params: list[Any],
) -> dict[str, int]:
    """Run FTS5 keyword search. Returns {id: rank} (rank 0 = best)."""
    rows = conn.execute(
        f"""
        SELECT s.id, bm25(standards_fts) AS score
        FROM standards_fts
        JOIN standards s ON s.rowid = standards_fts.rowid
        WHERE standards_fts MATCH ? AND {filter_sql}
        ORDER BY score
        LIMIT ?
        """,
        [query, *filter_params, _FTS_CANDIDATES],
    ).fetchall()
    return {r["id"]: rank for rank, r in enumerate(rows)}


def _vector_search(
    conn: sqlite3.Connection,
    query: str,
    filter_sql: str,
    filter_params: list[Any],
) -> dict[str, int]:
    """Embed the query and brute-force cosine against stored vectors."""
    query_vec = embed_texts([query])[0]

    rows = conn.execute(
        f"""
        SELECT s.id, sv.embedding
        FROM standards s
        JOIN standards_vec sv ON sv.standard_id = s.id
        WHERE {filter_sql}
        """,
        filter_params,
    ).fetchall()

    if not rows:
        return {}

    ids = [r["id"] for r in rows]
    matrix = np.array(
        [np.frombuffer(r["embedding"], dtype=np.float32) for r in rows]
    )
    scores = matrix @ query_vec                # vectors are unit-normalized
    top_idx = np.argsort(-scores)[:_VEC_CANDIDATES]
    return {ids[i]: rank for rank, i in enumerate(top_idx)}


def _rrf_merge(
    *rank_maps: dict[str, int], limit: int
) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion. Returns [(id, score), ...] sorted best-first."""
    combined: dict[str, float] = {}
    for ranks in rank_maps:
        for doc_id, rank in ranks.items():
            combined[doc_id] = combined.get(doc_id, 0.0) + 1 / (_RRF_K + rank)
    ordered = sorted(combined.items(), key=lambda kv: kv[1], reverse=True)
    return ordered[:limit]


def _fetch_rows_preserving_order(
    conn: sqlite3.Connection, scored: list[tuple[str, float]]
) -> list[dict[str, Any]]:
    """Load full rows for the ranked IDs, keeping RRF order. Attaches _score."""
    if not scored:
        return []
    ids = [doc_id for doc_id, _ in scored]
    placeholders = ",".join("?" * len(ids))
    rows = conn.execute(
        f"SELECT * FROM standards WHERE id IN ({placeholders})",
        ids,
    ).fetchall()
    by_id = {r["id"]: _row_to_dict(r) for r in rows}
    return [
        {**by_id[doc_id], "_score": score}
        for doc_id, score in scored
        if doc_id in by_id
    ]


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a sqlite3.Row into a plain dict."""
    return {key: row[key] for key in row.keys()}
