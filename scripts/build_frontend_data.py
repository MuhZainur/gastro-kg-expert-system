"""Generate static JSON data files for the frontend in frontend/data/.

Outputs:
  frontend/data/cases/index.json
  frontend/data/cases/E001.json .. E013.json
  frontend/data/queries.json

Run:  python scripts/build_frontend_data.py
"""
from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

from rdflib import Literal, URIRef
from rdflib.namespace import RDF, RDFS

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app import engine  # noqa: E402
from backend.app.engine import GK  # noqa: E402
from backend.app.schemas import ConsultationRequest  # noqa: E402
from backend.app.services.consultation import run_consultation  # noqa: E402
from backend.app.store import get_store  # noqa: E402


def _json_cell(val: object):
    if val is None:
        return None
    if isinstance(val, Literal):
        py = val.toPython()
        return float(py) if isinstance(py, Decimal) else py
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, URIRef):
        return str(val)
    return val


def build_cases(out_dir: Path) -> list[dict]:
    store = get_store()
    cases_graph = engine.load_graph(engine.KNOWLEDGE, engine.CASES)
    cases_dir = out_dir / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)

    index: list[dict] = []
    encounters = sorted(cases_graph.subjects(RDF.type, GK.Encounter), key=str)

    for enc in encounters:
        cid = str(enc).split("#")[1]
        patient = next(cases_graph.subjects(GK.hadEncounter, enc))
        pid = str(patient).split("#")[1]
        raw_label = str(cases_graph.value(enc, RDFS.label) or cid)
        title = raw_label.split(": ", 1)[-1]

        age = int(cases_graph.value(patient, GK.age))
        risks = sorted(str(r).split("#")[1] for r in cases_graph.objects(patient, GK.hasRiskFactor))
        meds = sorted(
            [
                {"id": str(m).split("#")[1], "regular": (patient, GK.takesRegularly, m) in cases_graph}
                for m in set(cases_graph.objects(patient, GK.takesRegularly))
                | set(cases_graph.objects(patient, GK.takesMedication))
            ],
            key=lambda item: item["id"],
        )
        symptoms = []
        for obs in cases_graph.objects(enc, GK.hasObservation):
            sym = cases_graph.value(obs, GK.observedSymptom)
            answer = "yes"
            if sym is None:
                sym = cases_graph.value(obs, GK.deniedSymptom)
                answer = "no"
            cf = float(cases_graph.value(obs, GK.userCF))
            symptoms.append({"id": str(sym).split("#")[1], "answer": answer, "certainty": round(cf, 1)})
        symptoms.sort(key=lambda item: item["id"])

        req_dict = {
            "age": age,
            "riskFactors": risks,
            "medications": meds,
            "symptoms": symptoms,
            "disabledRules": [],
            "extraKnowledge": None,
        }
        result = run_consultation(
            store,
            ConsultationRequest(**req_dict),
            patient_id=pid,
            encounter_id=cid,
            encounter_label=raw_label,
            precomputed=True,
        )
        case_payload = {
            "id": cid,
            "title": title,
            "request": req_dict,
            "result": result,
        }
        _write_json(cases_dir / f"{cid}.json", case_payload)

        top = result["hypotheses"][0] if result["hypotheses"] else None
        index.append({
            "id": cid,
            "title": title,
            "triage": {
                "level": result["triage"]["level"],
                "label": result["triage"]["label"],
                "labelId": result["triage"]["labelId"],
            } if result["triage"] else None,
            "topDisease": {
                "id": top["disease"]["id"],
                "label": top["disease"]["label"],
                "cf": top["cf"],
                "status": top["status"],
            } if top else None,
        })

    _write_json(cases_dir / "index.json", index)
    return index


def build_queries(out_dir: Path) -> list[dict]:
    reasoned = engine.reason_all_cases().graph
    queries_dir = ROOT / "graphdb" / "queries"
    items: list[dict] = []
    for path in sorted(queries_dir.glob("cq*.rq")):
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        title = lines[0][2:].strip() if lines and lines[0].startswith("# ") else path.stem
        res = reasoned.query(text)
        columns = [str(v) for v in res.vars]
        rows = [[_json_cell(cell) for cell in row] for row in res]
        items.append({
            "id": path.stem.split("-", 1)[0],
            "title": title,
            "query": text,
            "columns": columns,
            "rows": rows,
        })
    _write_json(out_dir / "queries.json", items)
    return items


def _write_json(path: Path, data: object) -> None:
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def main() -> None:
    out_dir = ROOT / "frontend" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    index = build_cases(out_dir)
    queries = build_queries(out_dir)
    print(f"wrote {len(index)} cases and {len(queries)} competency questions to {out_dir}")


if __name__ == "__main__":
    main()
