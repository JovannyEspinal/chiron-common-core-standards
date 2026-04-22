from __future__ import annotations
from dataclasses import dataclass

@dataclass
class StandardRow:
    id: str
    notation_short: str | None
    notation_full: str | None
    description: str
    grade: str
    subject: str
    jurisdiction: str
    set_id: str
    depth: int
    position: int
    parent_id: str
    ancestor_ids: str
    statement_label: str | None
    source_url: str | None