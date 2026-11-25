import pytest
from backend.tests.conftest import case_request

GOLDEN = [
    ("E001", "PrimaryCare", "GERD", 0.986688, "FullRuleMatch", 6, 0, "G08", 2),
    ("E002", "PrimaryCare", "Gastritis", 0.857728, "FullRuleMatch", 6, 0, "G04", 2),
    ("E003", "PrimaryCare", "Dyspepsia", 0.876096, "PartialMatch", 6, 0, "G05", 2),
    ("E004", "Emergency", "PepticUlcer", 0.824, "WeakMatch", 6, 0, None, 0),
    ("E005", "Urgent", "StomachCancer", 0.76288, "PartialMatch", 4, 0, "G01", 1),
    ("E006", "Referral", "Gastritis", 0.7264, "PartialMatch", 6, 0, "G05", 2),
    ("E007", "PrimaryCare", "PepticUlcer", 0.91144, "FullRuleMatch", 6, 3, "G13", 2),
    ("E008", "PrimaryCare", "Gastritis", 0.48, "WeakMatch", 6, 1, "G04", 1),
    ("E009", "PrimaryCare", "Gastroparesis", 0.9290368, "FullRuleMatch", 6, 1, "G01", 2),
    ("E010", "SelfMonitor", "Dyspepsia", 0.16, "WeakMatch", 3, 0, "G10", 0),
    ("E011", "PrimaryCare", "Gastritis", 0.7696, "PartialMatch", 6, 0, "G10", 2),
    ("E012", "PrimaryCare", "Gastritis", 0.7264, "PartialMatch", 6, 0, "G05", 2),
    ("E013", "Emergency", "GERD", 0.64, "WeakMatch", 3, 0, None, 0),
]


@pytest.mark.parametrize(
    "case_id,triage,rank1,cf,status,hyp_count,alert_count,next_q,advice_count",
    GOLDEN,
    ids=[g[0] for g in GOLDEN],
)
def test_golden_parity(client, case_id, triage, rank1, cf, status, hyp_count, alert_count, next_q, advice_count):
    r = client.post("/api/consultations", json=case_request(case_id))
    assert r.status_code == 200
    body = r.json()
    assert body["triage"]["level"] == triage
    assert len(body["hypotheses"]) == hyp_count
    h1 = body["hypotheses"][0]
    assert h1["disease"]["id"] == rank1
    assert h1["status"] == status
    assert abs(h1["cf"] - cf) < 1e-9
    assert len(body["alerts"]) == alert_count
    got_next = body["nextQuestion"]["code"] if body["nextQuestion"] else None
    assert got_next == next_q
    assert len(body["recommendations"]) == advice_count

    # Graph integrity
    graph = body["graph"]
    assert graph["focus"].startswith("gkd:")
    assert graph["focus"] in graph["nodes"]
    for s, _p, o, origin, reason_idx in graph["triples"]:
        assert s in graph["nodes"]
        assert o in graph["nodes"]
        assert origin in {"f", "d", "o", "r"}
        assert 0 <= reason_idx < len(graph["reasons"])
        assert graph["reasons"][reason_idx]


def test_slide_example_trace_and_special_values(client):
    e001 = client.post("/api/consultations", json=case_request("E001")).json()
    afters = [s["after"] for s in e001["hypotheses"][0]["steps"]]
    assert [round(x, 6) for x in afters] == [0.8, 0.896, 0.9792, 0.986688]

    e007 = client.post("/api/consultations", json=case_request("E007")).json()
    assert abs(e007["hypotheses"][1]["cf"] - 0.872) < 1e-9
    assert abs(e007["hypotheses"][2]["cf"] - 0.872) < 1e-9

    e011 = client.post("/api/consultations", json=case_request("E011")).json()
    gerd = next(h for h in e011["hypotheses"] if h["disease"]["id"] == "GERD")
    assert abs(gerd["cf"] - 0.542857142857) < 1e-9


def test_disabling_age_rule_and_all_rules(client):
    req6 = case_request("E006")
    req6["disabledRules"] = ["72-triage-age"]
    r6 = client.post("/api/consultations", json=req6)
    assert r6.status_code == 200
    assert r6.json()["triage"]["level"] != "Referral"

    req1 = case_request("E001")
    req1["disabledRules"] = ["72-triage-age"]
    r1 = client.post("/api/consultations", json=req1)
    assert r1.json()["triage"]["level"] == "PrimaryCare"

    all_rules = [item["name"] for item in client.get("/api/rules").json()["rules"]]
    req_none = case_request("E001")
    req_none["disabledRules"] = all_rules
    r_none = client.post("/api/consultations", json=req_none)
    assert r_none.status_code == 200
    body = r_none.json()
    assert body["triage"] is None
    assert body["hypotheses"] == []
    assert body["nextQuestion"] is None


def test_custom_knowledge_presets(client):
    req = case_request("E001")
    req["extraKnowledge"] = """
        @prefix gk:  <http://example.org/gastrokg/ontology#> .
        @prefix gkd: <http://example.org/gastrokg/data#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        gkd:Diclofenac a gk:Medication ; rdfs:label "Diclofenac"@en ; gk:drugClass gkd:NSAID .
    """
    req["medications"] = [{"id": "Diclofenac", "regular": True}]
    r = client.post("/api/consultations", json=req)
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["customKnowledge"] is True
    assert any(m["id"] == "Diclofenac" for a in body["alerts"] for m in a["medicines"])

    req_rule = case_request("E001")
    req_rule["symptoms"].append({"id": "CoughHoarseness", "answer": "yes", "certainty": 0.8})
    req_rule["extraKnowledge"] = """
        @prefix gk:  <http://example.org/gastrokg/ontology#> .
        @prefix gkd: <http://example.org/gastrokg/data#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix dcterms: <http://purl.org/dc/terms/> .
        gkd:R8 a gk:DiagnosticRule ;
            rdfs:label "R8: Heartburn and cough -> GERD"@en ;
            gk:code "R8" ;
            gk:concludes gkd:GERD ;
            gk:requiresSymptom gkd:Heartburn , gkd:CoughHoarseness ;
            dcterms:source gkd:GroupAssignment .
    """
    r2 = client.post("/api/consultations", json=req_rule)
    assert r2.status_code == 200
    assert any(m["rule"] == "R8" and m["fired"] for m in r2.json()["ruleMatches"])
