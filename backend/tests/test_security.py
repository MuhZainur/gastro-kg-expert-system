import json
import logging
import pytest


def valid_req():
    return {
        "age": 40,
        "riskFactors": [],
        "medications": [],
        "symptoms": [{"id": "EpigastricPain", "answer": "yes", "certainty": 0.8}],
        "disabledRules": [],
        "extraKnowledge": None,
    }


def test_s01_injection_ids_rejected(client):
    for bad in ["UnknownId", "EpigastricPain> <script>", 'Bad"Id', "Bad{Id}"]:
        req = valid_req()
        req["symptoms"][0]["id"] = bad
        r = client.post("/api/consultations", json=req)
        assert r.status_code == 422
        assert bad not in r.text


def test_s02_body_limit_with_and_without_content_length(client):
    big_payload = json.dumps({**valid_req(), "extraKnowledge": "a" * 70000}).encode("utf-8")
    r1 = client.post("/api/consultations", content=big_payload, headers={"Content-Type": "application/json"})
    assert r1.status_code == 413

    # Simulated streaming body without Content-Length header
    def gen():
        for i in range(0, len(big_payload), 8192):
            yield big_payload[i:i + 8192]

    r2 = client.post("/api/consultations", content=gen(), headers={"Content-Type": "application/json"})
    assert r2.status_code == 413


@pytest.mark.parametrize(
    "turtle",
    [
        "gkd:X owl:sameAs gkd:GERD .",
        "gkd:X rdfs:subClassOf gk:Symptom .",
        "gkd:X a owl:TransitiveProperty .",
        "gkd:X a sh:NodeShape .",
        "gkd:Ibuprofen a gk:Medication ; gk:drugClass gkd:NSAID .",
        "<http://evil.example/X> a gk:Medication ; gk:drugClass gkd:NSAID .",
        "[] a gk:Medication ; gk:drugClass gkd:NSAID .",
        "not valid turtle {{{",
        '{"@id": "http://example.org/gastrokg/data#X"}',
        "gkd:R1 a gk:DiagnosticRule ; gk:code \"R99\" ; gk:concludes gkd:GERD ; gk:requiresSymptom gkd:Heartburn , gkd:Nausea ; dcterms:source gkd:GroupAssignment .",
        "gkd:X a gk:Medication ; gk:drugClass gkd:NSAID ; rdfs:label \"" + ("a" * 201) + "\"@en .",
    ],
)
def test_s04_custom_knowledge_rejects_abuse(client, turtle):
    prefix = (
        "@prefix gk: <http://example.org/gastrokg/ontology#> .\n"
        "@prefix gkd: <http://example.org/gastrokg/data#> .\n"
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
        "@prefix sh: <http://www.w3.org/ns/shacl#> .\n"
        "@prefix dcterms: <http://purl.org/dc/terms/> .\n"
    )
    body = turtle if turtle.startswith("{") or turtle.startswith("not valid") else prefix + turtle
    r = client.post("/api/consultations", json={**valid_req(), "extraKnowledge": body})
    assert r.status_code == 422


def test_s04_custom_knowledge_size_and_triple_caps(client):
    prefix = "@prefix gk: <http://example.org/gastrokg/ontology#> .\n@prefix gkd: <http://example.org/gastrokg/data#> .\n"
    triples_40 = prefix + "\n".join(f"gkd:M{i} a gk:Medication ; gk:drugClass gkd:NSAID ." for i in range(20))
    assert len(triples_40.encode("utf-8")) <= 4096
    r40 = client.post("/api/consultations", json={**valid_req(), "extraKnowledge": triples_40})
    assert r40.status_code == 200

    triples_42 = prefix + "\n".join(f"gkd:M{i} a gk:Medication ; gk:drugClass gkd:NSAID ." for i in range(21))
    r42 = client.post("/api/consultations", json={**valid_req(), "extraKnowledge": triples_42})
    assert r42.status_code == 422

    pad = "# " + ("a" * (4097 - len(prefix) - 40)) + "\ngkd:M1 a gk:Medication ; gk:drugClass gkd:NSAID .\n"
    long_turtle = prefix + pad
    assert len(long_turtle.encode("utf-8")) > 4096
    r_big = client.post("/api/consultations", json={**valid_req(), "extraKnowledge": long_turtle})
    assert r_big.status_code == 422


def test_s05_no_sparql_endpoint(client):
    for path in ("/api/sparql", "/sparql", "/statements"):
        assert client.get(path).status_code == 404
        assert client.post(path).status_code == 404


def test_s06_sparql_load_graphs_disabled(client):
    import rdflib.plugins.sparql as sparql_mod
    assert sparql_mod.SPARQL_LOAD_GRAPHS is False


def test_s09_cors_exact_origins(client):
    for origin in ("https://evil.example", "https://other-project.vercel.app"):
        r = client.get("/api/health", headers={"Origin": origin})
        assert "access-control-allow-origin" not in r.headers

    r_ok = client.get("/api/health", headers={"Origin": "http://127.0.0.1:5500"})
    assert r_ok.headers.get("access-control-allow-origin") == "http://127.0.0.1:5500"


def test_s10_no_leaks_and_docs_off(client, monkeypatch):
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404

    r_bad_json = client.post("/api/consultations", content=b"{SECRET_ECHO_MARKER", headers={"Content-Type": "application/json"})
    assert r_bad_json.status_code == 422
    assert "SECRET_ECHO_MARKER" not in r_bad_json.text
    assert "Traceback" not in r_bad_json.text

    def boom(*_args, **_kwargs):
        raise RuntimeError("secret-db-path-C:\\Users\\acer\\leak rdflib")

    monkeypatch.setattr("backend.app.routers.consultations.run_consultation", boom)
    r500 = client.post("/api/consultations", json=valid_req())
    assert r500.status_code == 500
    body = r500.json()
    assert body["errors"][0]["code"] == "internal"
    assert "requestId" in body
    for forbidden in ("Traceback", "secret-db-path", "rdflib", "RuntimeError", "Users"):
        assert forbidden not in r500.text


def test_s11_no_body_logs(client, caplog):
    caplog.set_level(logging.INFO)
    req = {
        "age": 77,
        "riskFactors": ["Smoking"],
        "medications": [{"id": "Warfarin", "regular": True}],
        "symptoms": [{"id": "EpigastricPain", "answer": "yes", "certainty": 0.9}],
        "disabledRules": [],
        "extraKnowledge": None,
    }
    r = client.post("/api/consultations", json=req)
    assert r.status_code == 200
    assert r.headers.get("cache-control") == "no-store"
    logs = "\n".join(rec.getMessage() for rec in caplog.records)
    for sensitive in ("Warfarin", "EpigastricPain", "Smoking", "77"):
        assert sensitive not in logs


def test_s14_path_traversal_blocked(client):
    for path in ("/api/ontology/..%2F..%2Fpyproject.toml", "/api/ontology/pyproject.toml", "/api/ontology/evil"):
        assert client.get(path).status_code == 404


def test_s08_frontend_security_headers_config():
    from scripts.serve_frontend import load_security_headers

    headers = {k.lower(): v for k, v in load_security_headers()}
    csp = headers["content-security-policy"]
    assert "default-src 'none'" in csp
    assert "script-src 'self'" in csp
    assert "style-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "unsafe-inline" not in csp
    assert "unsafe-eval" not in csp
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "no-referrer"
    assert "permissions-policy" in headers


def test_s07_no_unsafe_js_sinks_or_storage():
    from pathlib import Path
    import re

    frontend = Path(__file__).resolve().parents[2] / "frontend"
    forbidden = re.compile(r"(innerHTML|dangerouslySetInnerHTML|\beval\s*\(|new Function|localStorage|sessionStorage|document\.cookie)")
    for js in frontend.rglob("*.js"):
        if "vendor" in js.parts:
            continue
        text = js.read_text(encoding="utf-8")
        assert not forbidden.search(text), f"Unsafe pattern in {js}"


def test_s13_vendor_hash_matches():
    import hashlib
    from pathlib import Path

    vendor = Path(__file__).resolve().parents[2] / "frontend" / "vendor"
    target = vendor / "htm-preact-standalone.module.js"
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    readme = (vendor / "README.md").read_text(encoding="utf-8")
    assert digest in readme
