"""Unit tests for chiron_standards.transform."""
from __future__ import annotations

import json

from chiron_standards.models import StandardRow
from chiron_standards.transform import SUBJECT_MAP, to_row


def _base_std() -> dict:
    """Minimal-but-valid standard dict matching the CSP API shape."""
    return {
        "id": "ABCDEF",
        "description": "Some description",
        "depth": 2,
        "position": 1000,
    }


def test_subject_map_known_subjects():
    assert SUBJECT_MAP["Common Core English/Language Arts"] == "ELA"
    assert SUBJECT_MAP["Common Core Mathematics"] == "Math"


def test_to_row_required_fields_only():
    """A standard with only required fields should still produce a valid row."""
    row = to_row(_base_std(), grade="03", subject="ELA", jurisdiction="CCSS", set_id="SET1")

    assert isinstance(row, StandardRow)
    assert row.id == "ABCDEF"
    assert row.description == "Some description"
    assert row.depth == 2
    assert row.position == 1000
    assert row.grade == "03"
    assert row.subject == "ELA"
    assert row.jurisdiction == "CCSS"
    assert row.set_id == "SET1"

    # Optional fields should default to None
    assert row.notation_short is None
    assert row.notation_full is None
    assert row.parent_id is None
    assert row.statement_label is None
    assert row.source_url is None

    # ancestor_ids should be valid JSON for an empty list
    assert json.loads(row.ancestor_ids) == []


def test_to_row_full_payload():
    """All fields populated from the API should map correctly."""
    std = {
        "id": "XYZ",
        "altStatementNotation": "L.3.6",
        "statementNotation": "CCSS.ELA-Literacy.L.3.6",
        "description": "Vocabulary standard",
        "depth": 2,
        "position": 500,
        "parentId": "PARENT123",
        "ancestorIds": ["PARENT123", "GRANDPARENT"],
        "statementLabel": "Standard",
        "exactMatch": ["http://corestandards.org/L/3/6", "XYZ"],
    }
    row = to_row(std, grade="03", subject="ELA", jurisdiction="CCSS", set_id="SET1")

    assert row.notation_short == "L.3.6"
    assert row.notation_full == "CCSS.ELA-Literacy.L.3.6"
    assert row.parent_id == "PARENT123"
    assert json.loads(row.ancestor_ids) == ["PARENT123", "GRANDPARENT"]
    assert row.statement_label == "Standard"
    assert row.source_url == "http://corestandards.org/L/3/6"


def test_to_row_source_url_skips_non_url_exact_match():
    """exactMatch sometimes has a GUID first; only real URLs become source_url."""
    std = {**_base_std(), "exactMatch": ["ABCDEF", "something-else"]}
    row = to_row(std, grade="03", subject="ELA", jurisdiction="CCSS", set_id="SET1")
    assert row.source_url is None


def test_to_row_handles_missing_exact_match():
    """Missing exactMatch must not crash and should leave source_url as None."""
    row = to_row(_base_std(), grade="03", subject="ELA", jurisdiction="CCSS", set_id="SET1")
    assert row.source_url is None


def test_to_row_handles_empty_ancestor_ids():
    """Missing/empty ancestorIds should produce a valid empty JSON array."""
    std = {**_base_std(), "ancestorIds": []}
    row = to_row(std, grade="03", subject="ELA", jurisdiction="CCSS", set_id="SET1")
    assert json.loads(row.ancestor_ids) == []
