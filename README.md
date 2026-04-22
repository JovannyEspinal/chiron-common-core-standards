# chiron-common-core-standards

[![PyPI](https://img.shields.io/pypi/v/chiron-common-core-standards.svg)](https://pypi.org/project/chiron-common-core-standards/)
[![Python](https://img.shields.io/pypi/pyversions/chiron-common-core-standards.svg)](https://pypi.org/project/chiron-common-core-standards/)
[![License](https://img.shields.io/pypi/l/chiron-common-core-standards.svg)](https://github.com/JovannyEspinal/chiron-common-core-standards/blob/main/LICENSE)

An MCP (Model Context Protocol) server that exposes US Common Core ELA standards (grades 2–4) as lookup tools for LLM agents.

> Package name on PyPI: `chiron-common-core-standards`. Python import name: `chiron_standards`.

Backed by a bundled SQLite database with full-text and semantic search — no network calls at runtime, no external rate limits.

## Why

When an LLM generates educational content — worksheets, assessments, lesson plans — it needs to align to real educational standards. Without a reliable lookup tool, models hallucinate standard codes, misremember descriptions, or attach the wrong grade level. `chiron-standards` gives agents a grounded, deterministic source for Common Core lookups.

## Features

- **Three tools**:
  - `get_standard(code_or_id)` — exact lookup by notation (e.g. `"RL.3.1"`) or GUID
  - `list_standards(jurisdiction, grade, subject)` — full tree for a standard set
  - `search_standards(query, grade, subject, limit)` — hybrid FTS5 + semantic search with Reciprocal Rank Fusion
- **Offline** — all ~500 Common Core ELA standards (grades 2–4) ship inside the wheel as a pre-built SQLite file with embeddings
- **Semantic search** powered by OpenAI `text-embedding-3-small` (only `search_standards` requires an `OPENAI_API_KEY`; the other two tools are fully offline)
- **Leaf-only search results** — parents, domains, and anchor standards are filtered out so agents align to alignable standards

## Install

```bash
pip install chiron-common-core-standards
```

## Use with Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "chiron-standards": {
      "command": "chiron-standards",
      "env": {
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

Restart Claude Desktop. The three tools will appear automatically.

## Use with the MCP Inspector (for development)

```bash
uv run fastmcp dev inspector src/chiron_standards/server.py
```

Open the printed URL, connect, and call tools manually.

## Use as a Python library

The same tools are available as plain Python functions — useful from your own backend without going through MCP:

```python
from chiron_standards.db import connect
from chiron_standards.queries import get_standard, search_standards

conn = connect()

# Exact lookup
print(get_standard(conn, "RL.3.1"))

# Semantic search (requires OPENAI_API_KEY in env)
hits = search_standards(conn, "finding evidence in a passage", grade="03", subject="ELA", limit=3)
for h in hits:
    print(h["notation_short"], h["description"])
```

## Data model

Each standard returns a dict with:

| field             | description                                                      |
| ----------------- | ---------------------------------------------------------------- |
| `id`              | 32-char GUID from Achievement Standards Network                  |
| `notation_short`  | Short notation (e.g. `"RL.3.1"`) — `null` for parent containers  |
| `notation_full`   | Formal notation (e.g. `"CCSS.ELA-Literacy.RL.3.1"`)              |
| `description`     | The standard text                                                |
| `grade`           | Two-digit grade (`"02"`, `"03"`, `"04"`)                         |
| `subject`         | Normalized subject (`"ELA"`)                                     |
| `jurisdiction`    | `"Common Core State Standards"`                                  |
| `set_id`          | Standard set GUID                                                |
| `depth`           | 0 = domain, 1 = cluster, 2 = standard, 3 = component             |
| `position`        | Original ordering within the document                            |
| `parent_id`       | GUID of the parent standard, or `null`                           |
| `ancestor_ids`    | JSON-encoded list of ancestor GUIDs                              |
| `statement_label` | `"Standard"`, `"Component"`, or `null`                           |
| `source_url`      | Canonical corestandards.org URL, when available                  |

`search_standards` results additionally include a `_score` field (higher = better).

## Build the database yourself

The published wheel already contains `standards.db`. To rebuild it (e.g. to pull fresh upstream data):

```bash
git clone https://github.com/JovannyEspinal/chiron-common-core-standards
cd chiron-common-core-standards
uv sync
cp .env.example .env   # add CSP_API_KEY and OPENAI_API_KEY
uv run python -m chiron_standards.ingest
```

This fetches Common Core ELA grades 2–4 from the [Common Standards Project API](https://commonstandardsproject.com/api/v1/), embeds descriptions with OpenAI, and writes `src/chiron_standards/data/standards.db`.

## Development

```bash
uv sync
uv run pytest                           # run the test suite
uv run fastmcp dev inspector src/chiron_standards/server.py
```

## License and attribution

- **Code**: Apache License 2.0 — see [LICENSE](LICENSE).
- **Data**: The standards data shipped in this package is sourced from the [Common Standards Project](https://commonstandardsproject.com), which aggregates releases from the [Achievement Standards Network](http://asn.desire2learn.com/) (ASN) operated by Desire2Learn. ASN's standards data is licensed under [CC BY 3.0 US](http://creativecommons.org/licenses/by/3.0/us/).
- **Common Core State Standards** © 2010 National Governors Association Center for Best Practices and Council of Chief State School Officers. All rights reserved.

See [NOTICE](NOTICE) for full attribution requirements.
