# GastroKG

A knowledge-graph expert system for screening upper gastrointestinal complaints. It continues our
earlier system (forward chaining with certainty factors) on RDF, RDFS, OWL 2 RL, SPARQL CONSTRUCT
and SHACL, wrapped with a FastAPI backend and a static Preact + htm web frontend.

Final project, Magister Kecerdasan Artifisial, Universitas Gadjah Mada, 2026.
Hasnan Husaini, Muhammad Zainurrahman, Nur Sekti Waskitha Jati.

> **Educational prototype, not a medical device.** The certainty weights are illustrative and have
> not been clinically validated. All patient cases are synthetic.

## Live deployment

- **Web App (Frontend)**: https://gastro-kg-expert-system-frontend.vercel.app/
- **API Base URL (Backend)**: https://gastro-kg-expert-system.vercel.app/ (health check: `/api/health`)

## Contents

| Path | Content |
|---|---|
| `ontology/gastrokg-tbox.ttl` | T-Box: classes, properties, OWL class definitions |
| `ontology/gastrokg-knowledge.ttl` | A-Box: 6 diseases, 22 symptoms, evidence weights, rules, drug safety |
| `ontology/gastrokg-cases.ttl` | A-Box: 13 synthetic patient cases |
| `rules/` | 30 SPARQL CONSTRUCT rules, applied in file-name order |
| `shapes/` | SHACL shapes |
| `graphdb/` | Repository config, SPARQL updates, materialised results, queries. See its README |
| `backend/` | FastAPI application (`backend/app/engine.py`, routers, services) and API/security tests |
| `frontend/` | Static Preact + `htm` web UI, vendored module, precomputed sample cases & queries |
| `scripts/` | Knowledge, rule, query, GraphDB, and frontend data generators; local static server |
| `tests/` | Engine competency/rule/SHACL tests and Playwright browser E2E tests |
| `docs/gastrokg-graph.html` | Expandable graph starting at patient case E007 |
| `docs/gastrokg-workflow.html` | One-page clickable workflow diagram (in Indonesian) |
| `docs/gastrokg-explorer.html` | Clickable map (in Indonesian): workflow, RDF/RDFS/OWL relations, graphs, case traces |

## Run locally (Python 3.12)

Using `uv`:

```
uv venv .venv312 --python 3.12
.venv312\Scripts\activate
uv pip install -e . --group dev
```

Or with standard `venv` + `pip`:

```
python -m venv .venv312
.venv312\Scripts\activate
pip install fastapi==0.165.0 rdflib==7.6.0 owlrl==7.6.2 pyshacl==0.40.2 uvicorn==0.54.0 httpx==0.28.1 pytest==9.2.0
```

Start the API and static frontend in two terminals:

```
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
python scripts/serve_frontend.py --port 5500
```

Open `http://127.0.0.1:5500/`.

Run automated checks:

```
pytest tests/test_engine.py backend/tests
python scripts/run_cases.py
```

## Changing the knowledge

The two A-Box files, the rules, the queries, and the frontend precomputed JSON files are generated.
Edit the tables in `scripts/`, then:

```
python scripts/make_knowledge.py
python scripts/make_rules.py
python scripts/make_queries.py
python scripts/build_graphdb.py
python scripts/make_explorer.py
python scripts/make_graph.py
python scripts/build_frontend_data.py
pytest
```

## Security & limitations

- No authentication; patient answers are held in memory only (`Cache-Control: no-store`, no database, no cookies/localStorage).
- No public SPARQL endpoint; free-form queries run locally in GraphDB (`graphdb/README.md`).
- Custom knowledge via the API is limited to a strict Turtle allow-list (4 KB, 40 triples, SHACL-checked).
