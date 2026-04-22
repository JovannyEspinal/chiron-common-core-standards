"""Build-time ingest: CSP API → SQLite (rows + embeddings + FTS5)."""
from __future__ import annotations

import json
import os
from dataclasses import asdict

from dotenv import load_dotenv

from chiron_standards.csp import CSPClient, ELA_SET_IDS
from chiron_standards.db import INSERT_STANDARD_SQL, connect, init_schema
from chiron_standards.embeddings import EMBED_MODEL, embed_texts
from chiron_standards.transform import SUBJECT_MAP, to_row


def ingest_standards(conn, client: CSPClient) -> int:
    """Fetch all ELA sets from the API and insert rows. Returns inserted count."""
    total = 0
    for set_id in ELA_SET_IDS:
        data = client.fetch_standard_set(set_id)
        grade = data["educationLevels"][0]
        subject = SUBJECT_MAP[data["subject"]]
        jurisdiction = data["jurisdiction"]["title"]

        rows = [
            to_row(std, grade, subject, jurisdiction, data["id"])
            for std in data["standards"].values()
        ]
        conn.executemany(INSERT_STANDARD_SQL, [asdict(r) for r in rows])
        print(f"  grade {grade}: {len(rows)} rows")
        total += len(rows)
    return total


def embed_standards(conn) -> int:
    """Embed every description and store vectors + model metadata."""
    rows = conn.execute("SELECT id, description FROM standards").fetchall()
    ids = [r["id"] for r in rows]
    descriptions = [r["description"] for r in rows]

    vectors = embed_texts(descriptions)

    conn.executemany(
        "INSERT OR REPLACE INTO standards_vec (standard_id, embedding) VALUES (?, ?)",
        [(sid, vec.tobytes()) for sid, vec in zip(ids, vectors)],
    )
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
        ("embedding_model", EMBED_MODEL),
    )
    return len(ids)


def index_fts(conn) -> int:
    """Rebuild the FTS5 index over descriptions + ancestor descriptions."""
    all_rows = conn.execute("SELECT id, description FROM standards").fetchall()
    id_to_desc = {r["id"]: r["description"] for r in all_rows}

    fts_rows = []
    for row in conn.execute(
        "SELECT rowid, id, description, ancestor_ids FROM standards"
    ).fetchall():
        ancestor_ids = json.loads(row["ancestor_ids"])
        ancestor_descs = " ".join(
            id_to_desc[aid] for aid in ancestor_ids if aid in id_to_desc
        )
        fts_rows.append((row["rowid"], row["description"], ancestor_descs))

    conn.execute("INSERT INTO standards_fts(standards_fts) VALUES('delete-all')")
    conn.executemany(
        "INSERT INTO standards_fts(rowid, description, ancestor_descriptions) "
        "VALUES (?, ?, ?)",
        fts_rows,
    )
    return len(fts_rows)


if __name__ == "__main__":
    load_dotenv()

    conn = connect()
    init_schema(conn)
    print(f"DB path: {conn.execute('PRAGMA database_list').fetchone()[2]}")

    client = CSPClient(api_key=os.environ["CSP_API_KEY"])

    inserted = ingest_standards(conn, client)
    print("embedding...")
    embedded = embed_standards(conn)
    print("indexing FTS5...")
    indexed = index_fts(conn)

    conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM standards").fetchone()[0]
    print(
        f"inserted: {inserted} | embedded: {embedded} | "
        f"fts: {indexed} | total in DB: {total}"
    )
