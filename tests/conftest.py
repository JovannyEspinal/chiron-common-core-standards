"""Shared pytest fixtures for chiron-standards tests."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict

import numpy as np
import pytest

from chiron_standards.db import INSERT_STANDARD_SQL, init_schema
from chiron_standards.models import StandardRow


# A small but representative set of fixture rows covering:
#   - a depth-0 domain (no notation)
#   - a depth-1 cluster (no notation)
#   - a depth-2 anchor standard (CCR.* — should be excluded by search)
#   - depth-2 leaf standards across RL, RI, SL
#   - a depth-3 component
SAMPLE_ROWS = [
    StandardRow(
        id="DOM1",
        notation_short=None,
        notation_full=None,
        description="Reading Standards for Informational Text",
        grade="03",
        subject="ELA",
        jurisdiction="Common Core State Standards",
        set_id="SET_G3",
        depth=0,
        position=1000,
        parent_id=None,
        ancestor_ids=json.dumps([]),
        statement_label=None,
        source_url=None,
    ),
    StandardRow(
        id="CLU1",
        notation_short=None,
        notation_full=None,
        description="Key Ideas and Details",
        grade="03",
        subject="ELA",
        jurisdiction="Common Core State Standards",
        set_id="SET_G3",
        depth=1,
        position=2000,
        parent_id="DOM1",
        ancestor_ids=json.dumps(["DOM1"]),
        statement_label=None,
        source_url=None,
    ),
    StandardRow(
        id="CCR_R_1",
        notation_short="CCR.R.1",
        notation_full="CCSS.ELA-Literacy.CCRA.R.1",
        description="Read closely to determine what the text says explicitly.",
        grade="03",
        subject="ELA",
        jurisdiction="Common Core State Standards",
        set_id="SET_G3",
        depth=2,
        position=3000,
        parent_id="CLU1",
        ancestor_ids=json.dumps(["CLU1", "DOM1"]),
        statement_label="Standard",
        source_url="http://corestandards.org/ELA-Literacy/CCRA/R/1",
    ),
    StandardRow(
        id="RI_3_1",
        notation_short="RI.3.1",
        notation_full="CCSS.ELA-Literacy.RI.3.1",
        description="Ask and answer questions to demonstrate understanding of a text, "
        "referring explicitly to the text as the basis for the answers.",
        grade="03",
        subject="ELA",
        jurisdiction="Common Core State Standards",
        set_id="SET_G3",
        depth=2,
        position=4000,
        parent_id="CLU1",
        ancestor_ids=json.dumps(["CLU1", "DOM1"]),
        statement_label="Standard",
        source_url="http://corestandards.org/ELA-Literacy/RI/3/1",
    ),
    StandardRow(
        id="RI_3_2",
        notation_short="RI.3.2",
        notation_full="CCSS.ELA-Literacy.RI.3.2",
        description="Determine the main idea of a text; recount the key details and "
        "explain how they support the main idea.",
        grade="03",
        subject="ELA",
        jurisdiction="Common Core State Standards",
        set_id="SET_G3",
        depth=2,
        position=5000,
        parent_id="CLU1",
        ancestor_ids=json.dumps(["CLU1", "DOM1"]),
        statement_label="Standard",
        source_url="http://corestandards.org/ELA-Literacy/RI/3/2",
    ),
    StandardRow(
        id="SL_3_2",
        notation_short="SL.3.2",
        notation_full="CCSS.ELA-Literacy.SL.3.2",
        description="Determine the main ideas and supporting details of a text "
        "read aloud or information presented in diverse media.",
        grade="03",
        subject="ELA",
        jurisdiction="Common Core State Standards",
        set_id="SET_G3",
        depth=2,
        position=6000,
        parent_id=None,
        ancestor_ids=json.dumps([]),
        statement_label="Standard",
        source_url=None,
    ),
    StandardRow(
        id="RL_2_1",
        notation_short="RL.2.1",
        notation_full="CCSS.ELA-Literacy.RL.2.1",
        description="Ask and answer such questions as who, what, where, when, why, "
        "and how to demonstrate understanding of key details in a text.",
        grade="02",
        subject="ELA",
        jurisdiction="Common Core State Standards",
        set_id="SET_G2",
        depth=2,
        position=7000,
        parent_id=None,
        ancestor_ids=json.dumps([]),
        statement_label="Standard",
        source_url=None,
    ),
    StandardRow(
        id="L_3_5_a",
        notation_short="L.3.5.a",
        notation_full="CCSS.ELA-Literacy.L.3.5a",
        description="Distinguish the literal and nonliteral meanings of words.",
        grade="03",
        subject="ELA",
        jurisdiction="Common Core State Standards",
        set_id="SET_G3",
        depth=3,
        position=8000,
        parent_id="RI_3_2",  # arbitrary; just needs a parent
        ancestor_ids=json.dumps(["RI_3_2", "CLU1", "DOM1"]),
        statement_label="Component",
        source_url=None,
    ),
]


def _deterministic_vector(seed: int, dim: int = 1536) -> np.ndarray:
    """Produce a reproducible unit vector from an integer seed."""
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim).astype(np.float32)
    v /= np.linalg.norm(v)
    return v


@pytest.fixture
def conn() -> sqlite3.Connection:
    """In-memory DB with schema + sample rows + deterministic embeddings + FTS5."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    init_schema(conn)

    # Insert rows
    conn.executemany(INSERT_STANDARD_SQL, [asdict(r) for r in SAMPLE_ROWS])

    # Populate standards_vec with deterministic vectors keyed by row position
    for i, row in enumerate(SAMPLE_ROWS):
        vec = _deterministic_vector(seed=i)
        conn.execute(
            "INSERT INTO standards_vec (standard_id, embedding) VALUES (?, ?)",
            (row.id, vec.tobytes()),
        )

    # Populate FTS5
    id_to_desc = {r.id: r.description for r in SAMPLE_ROWS}
    for db_row in conn.execute(
        "SELECT rowid, id, description, ancestor_ids FROM standards"
    ).fetchall():
        ancestor_ids = json.loads(db_row["ancestor_ids"])
        ancestor_descs = " ".join(
            id_to_desc[aid] for aid in ancestor_ids if aid in id_to_desc
        )
        conn.execute(
            "INSERT INTO standards_fts(rowid, description, ancestor_descriptions) "
            "VALUES (?, ?, ?)",
            (db_row["rowid"], db_row["description"], ancestor_descs),
        )

    conn.commit()
    return conn


@pytest.fixture
def stub_embed_texts(monkeypatch):
    """Replace embeddings.embed_texts with a deterministic stub.

    Returns the embedding for RI.3.2's seed (so semantic search will point there
    for any query — tests assert the pipeline works, not OpenAI's quality).
    """
    target_seed = next(
        i for i, r in enumerate(SAMPLE_ROWS) if r.id == "RI_3_2"
    )
    target_vec = _deterministic_vector(seed=target_seed)

    def _fake(texts, client=None):
        return np.array([target_vec for _ in texts])

    monkeypatch.setattr("chiron_standards.queries.embed_texts", _fake)
    return target_vec
