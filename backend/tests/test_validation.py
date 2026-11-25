import pytest


def base_req(**overrides):
    req = {
        "age": 30,
        "riskFactors": [],
        "medications": [],
        "symptoms": [{"id": "EpigastricPain", "answer": "yes", "certainty": 0.8}],
        "disabledRules": [],
        "extraKnowledge": None,
    }
    req.update(overrides)
    return req


@pytest.mark.parametrize("age", [0, 120])
def test_age_boundaries_valid(client, age):
    r = client.post("/api/consultations", json=base_req(age=age))
    assert r.status_code == 200


@pytest.mark.parametrize("age", [-1, 121, 30.5, True, "30"])
def test_age_invalid(client, age):
    r = client.post("/api/consultations", json=base_req(age=age))
    assert r.status_code == 422


@pytest.mark.parametrize("certainty", [0.1, 1.0])
def test_certainty_boundaries_valid(client, certainty):
    r = client.post(
        "/api/consultations",
        json=base_req(symptoms=[{"id": "EpigastricPain", "answer": "yes", "certainty": certainty}]),
    )
    assert r.status_code == 200


@pytest.mark.parametrize("certainty", [0.0, 1.1, 0.55, -0.1, "0.5"])
def test_certainty_invalid(client, certainty):
    r = client.post(
        "/api/consultations",
        json=base_req(symptoms=[{"id": "EpigastricPain", "answer": "yes", "certainty": certainty}]),
    )
    assert r.status_code == 422


def test_symptoms_bounds_and_uniqueness(client):
    assert client.post("/api/consultations", json=base_req(symptoms=[])).status_code == 422
    assert client.post(
        "/api/consultations",
        json=base_req(symptoms=[
            {"id": "EpigastricPain", "answer": "yes", "certainty": 0.5},
            {"id": "EpigastricPain", "answer": "no", "certainty": 0.5},
        ]),
    ).status_code == 422
    assert client.post(
        "/api/consultations",
        json=base_req(symptoms=[{"id": "EpigastricPain", "answer": "maybe", "certainty": 0.5}]),
    ).status_code == 422

    # All 22 symptoms, all answered "no"
    form = client.get("/api/form").json()
    all_syms = [s["id"] for g in form["symptomGroups"] for s in g["symptoms"]]
    assert len(all_syms) == 22
    r = client.post(
        "/api/consultations",
        json=base_req(symptoms=[{"id": sid, "answer": "no", "certainty": 0.5} for sid in all_syms]),
    )
    assert r.status_code == 200

    # 23 items fails
    r23 = client.post(
        "/api/consultations",
        json=base_req(symptoms=[{"id": sid, "answer": "yes", "certainty": 0.5} for sid in all_syms] + [
            {"id": "EpigastricPain", "answer": "yes", "certainty": 0.5}
        ]),
    )
    assert r23.status_code == 422


def test_every_medicine_and_risk_factor(client):
    form = client.get("/api/form").json()
    meds = [{"id": m["id"], "regular": True} for m in form["medications"]]
    risks = [rf["id"] for rf in form["riskFactors"]]
    r = client.post("/api/consultations", json=base_req(medications=meds, riskFactors=risks))
    assert r.status_code == 200


def test_unknown_fields_and_duplicates_rejected(client):
    assert client.post("/api/consultations", json={**base_req(), "extraField": 1}).status_code == 422
    assert client.post("/api/consultations", json=base_req(riskFactors=["Smoking", "Smoking"])).status_code == 422
    assert client.post(
        "/api/consultations",
        json=base_req(medications=[{"id": "Ibuprofen", "regular": True}, {"id": "Ibuprofen", "regular": False}]),
    ).status_code == 422
    assert client.post(
        "/api/consultations",
        json=base_req(disabledRules=["01-manifestation", "01-manifestation"]),
    ).status_code == 422
    assert client.post(
        "/api/consultations",
        json=base_req(disabledRules=["99-nonexistent"]),
    ).status_code == 422
