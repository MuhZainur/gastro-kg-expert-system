def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "version": "1.0.0", "rules": 30}
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert r.headers["content-security-policy"] == "default-src 'none'; frame-ancestors 'none'"


def test_form_counts_and_shape(client):
    r = client.get("/api/form")
    assert r.status_code == 200
    body = r.json()
    groups = {g["id"]: g for g in body["symptomGroups"]}
    assert [g["id"] for g in body["symptomGroups"]] == ["warning", "dyspeptic", "reflux"]
    assert len(groups["warning"]["symptoms"]) == 9
    assert sum(1 for s in groups["warning"]["symptoms"] if s["level"] == "emergency") == 5
    assert sum(1 for s in groups["warning"]["symptoms"] if s["level"] == "alarm") == 4
    assert len(groups["dyspeptic"]["symptoms"]) == 9
    assert len(groups["reflux"]["symptoms"]) == 4
    assert len(body["riskFactors"]) == 6
    assert len(body["medications"]) == 8
    for s in groups["warning"]["symptoms"] + groups["dyspeptic"]["symptoms"] + groups["reflux"]["symptoms"]:
        assert {"id", "code", "label", "labelId", "altLabels"} <= s.keys()


def test_rules_endpoint(client):
    r = client.get("/api/rules")
    assert r.status_code == 200
    rules = r.json()["rules"]
    assert len(rules) == 30
    assert rules[0]["name"] == "01-manifestation"
    assert rules[-1]["name"] == "96-best-question"
    for item in rules:
        assert {"name", "group", "title", "description", "iterate", "query"} == item.keys()


def test_ontology_downloads(client):
    for name in ("tbox", "knowledge", "cases", "shapes"):
        r = client.get(f"/api/ontology/{name}")
        assert r.status_code == 200
        assert "text/turtle" in r.headers["content-type"]
        assert "attachment" in r.headers.get("content-disposition", "")


def test_consultation_response_shape_and_headers(client):
    from backend.tests.conftest import case_request

    r = client.post("/api/consultations", json=case_request("E007"))
    assert r.status_code == 200
    assert r.headers.get("cache-control") == "no-store"
    body = r.json()
    expected_keys = {
        "triage", "hypotheses", "ruleMatches", "owlFacts", "alerts",
        "recommendations", "nextQuestion", "graph", "meta", "disclaimer",
    }
    assert expected_keys == body.keys()
    assert body["meta"]["precomputed"] is False
    assert set(body["meta"]["seconds"].keys()) == {"shacl", "closure", "rules", "total"}
    assert body["hypotheses"][0]["disease"]["id"] == "PepticUlcer"
    assert isinstance(body["hypotheses"][0]["cf"], float)


def test_documented_error_codes(client):
    r404 = client.get("/api/ontology/unknown")
    assert r404.status_code == 404
    assert r404.json()["errors"][0]["code"] == "not_found"
    assert "requestId" in r404.json()

    r415 = client.post("/api/consultations", content=b"{}", headers={"Content-Type": "text/plain"})
    assert r415.status_code == 415
    assert r415.json()["errors"][0]["code"] == "unsupported_media_type"

    big = b'{"a":"' + b"x" * 70000 + b'"}'
    r413 = client.post("/api/consultations", content=big, headers={"Content-Type": "application/json"})
    assert r413.status_code == 413
    assert r413.json()["errors"][0]["code"] == "too_large"

    r422 = client.post("/api/consultations", json={"age": -1, "symptoms": []})
    assert r422.status_code == 422
    assert r422.json()["errors"][0]["code"] == "validation"
