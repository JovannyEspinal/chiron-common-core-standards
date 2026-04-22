"""Tests for chiron_standards.queries."""
from __future__ import annotations

from chiron_standards.queries import get_standard, list_standards, search_standards


# -- get_standard --------------------------------------------------------------

def test_get_standard_by_short_notation(conn):
    row = get_standard(conn, "RI.3.1")
    assert row is not None
    assert row["id"] == "RI_3_1"
    assert row["notation_short"] == "RI.3.1"


def test_get_standard_by_guid(conn):
    # Our fixture uses 6-char ids; lookup path requires length == 32 for GUID detection.
    # Use a realistic 32-char id to exercise the GUID branch.
    conn.execute(
        """
        INSERT INTO standards (id, description, grade, subject, jurisdiction,
                               set_id, depth, position, ancestor_ids)
        VALUES ('A39536851ADB47869604ABC9DFAB53E9', 'test', '03', 'ELA',
                'Common Core State Standards', 'SET_G3', 2, 9000, '[]')
        """
    )
    row = get_standard(conn, "A39536851ADB47869604ABC9DFAB53E9")
    assert row is not None
    assert row["id"] == "A39536851ADB47869604ABC9DFAB53E9"


def test_get_standard_returns_none_when_missing(conn):
    assert get_standard(conn, "DOES_NOT_EXIST") is None


# -- list_standards ------------------------------------------------------------

def test_list_standards_filters_by_grade_and_subject(conn):
    rows = list_standards(conn, grade="03", subject="ELA")
    ids = {r["id"] for r in rows}

    # All grade-3 ELA rows from the fixture should appear (including parents/anchors)
    assert {"DOM1", "CLU1", "CCR_R_1", "RI_3_1", "RI_3_2", "SL_3_2", "L_3_5_a"} <= ids
    # Grade 2 row should not
    assert "RL_2_1" not in ids


def test_list_standards_default_jurisdiction(conn):
    """Default jurisdiction is 'Common Core State Standards' — sanity check."""
    rows = list_standards(conn)
    assert len(rows) == 8  # all fixture rows


def test_list_standards_ordered_by_position(conn):
    rows = list_standards(conn, grade="03", subject="ELA")
    positions = [r["position"] for r in rows]
    assert positions == sorted(positions)


# -- search_standards ----------------------------------------------------------

def test_search_standards_excludes_parents_and_anchors(conn, stub_embed_texts):
    """Domains, clusters, and CCR anchors should never appear in search results."""
    results = search_standards(conn, "main idea", grade="03", subject="ELA", limit=10)
    ids = {r["id"] for r in results}

    assert "DOM1" not in ids       # depth 0
    assert "CLU1" not in ids       # depth 1
    assert "CCR_R_1" not in ids    # depth 2 but anchor (CCR.*)


def test_search_standards_returns_leaves_only(conn, stub_embed_texts):
    """All results must be depth >= 2 and not CCR.*"""
    results = search_standards(conn, "main idea", grade="03", subject="ELA", limit=10)
    for r in results:
        assert r["depth"] >= 2
        assert r["notation_short"] is None or not r["notation_short"].startswith("CCR.")


def test_search_standards_respects_grade_filter(conn, stub_embed_texts):
    """grade='03' must exclude the grade-2 fixture row."""
    results = search_standards(conn, "ask questions", grade="03", subject="ELA", limit=10)
    ids = {r["id"] for r in results}
    assert "RL_2_1" not in ids


def test_search_standards_attaches_score(conn, stub_embed_texts):
    results = search_standards(conn, "main idea", grade="03", subject="ELA", limit=3)
    assert results, "expected at least one result"
    for r in results:
        assert "_score" in r
        assert isinstance(r["_score"], float)
        assert r["_score"] > 0


def test_search_standards_vector_only_path(conn, stub_embed_texts):
    """Even when FTS5 returns nothing, vector search should still produce results."""
    results = search_standards(conn, "xyzzy_no_match", grade="03", subject="ELA", limit=3)
    # The stub embed_texts always returns RI.3.2's vector, so that should rank top
    assert results
    assert results[0]["id"] == "RI_3_2"


def test_search_standards_empty_when_no_filter_matches(conn, stub_embed_texts):
    """If filters exclude every row, both searches return nothing."""
    results = search_standards(conn, "main idea", grade="99", subject="ELA", limit=3)
    assert results == []
