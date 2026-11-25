import json
from pathlib import Path
from scripts.build_frontend_data import build_queries


def test_stored_queries_match_generator(tmp_path):
    committed = Path(__file__).resolve().parents[2] / "frontend" / "data" / "queries.json"
    assert committed.exists(), "Run scripts/build_frontend_data.py first."
    build_queries(tmp_path)
    generated = json.loads((tmp_path / "queries.json").read_text(encoding="utf-8"))
    actual = json.loads(committed.read_text(encoding="utf-8"))
    assert generated == actual
    assert len(actual) == 14


def test_stored_cases_index_and_files_exist():
    cases_dir = Path(__file__).resolve().parents[2] / "frontend" / "data" / "cases"
    index = json.loads((cases_dir / "index.json").read_text(encoding="utf-8"))
    assert len(index) == 13
    for item in index:
        case_file = cases_dir / f"{item['id']}.json"
        assert case_file.exists()
        payload = json.loads(case_file.read_text(encoding="utf-8"))
        assert payload["result"]["meta"]["precomputed"] is True
        assert payload["result"]["meta"]["seconds"] is None
