from chiron_standards.models import StandardRow
import json

SUBJECT_MAP = {
    "Common Core English/Language Arts": "ELA",
    "Common Core Mathematics": "Math",
}

def to_row(std: dict, grade: str, subject: str, jurisdiction: str, set_id: str) -> StandardRow:
    exact_match = std.get("exactMatch") or []
    source_url = exact_match[0] if exact_match and exact_match[0].startswith("http") else None
    ancestor_ids = json.dumps(std.get("ancestorIds") or [])

    return StandardRow(
        id=std["id"],
        notation_short=std.get("altStatementNotation"),
        notation_full=std.get("statementNotation"),
        description=std["description"],
        grade=grade,
        subject=subject,
        jurisdiction=jurisdiction,
        set_id=set_id,
        depth=std["depth"],
        position=std["position"],
        parent_id=std.get("parentId"),
        ancestor_ids=ancestor_ids,
        statement_label=std.get("statementLabel"),
        source_url=source_url
    )