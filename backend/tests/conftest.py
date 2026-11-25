import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    from backend.app.main import create_app

    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def case_request(case_id: str) -> dict:
    """Build a /api/consultations request payload directly from gastrokg-cases.ttl triples."""
    from rdflib.namespace import RDF
    from backend.app import engine
    from backend.app.engine import GK, GKD

    g = engine.load_graph(engine.KNOWLEDGE, engine.CASES)
    enc = GKD[case_id]
    patient = next(g.subjects(GK.hadEncounter, enc))
    age = int(g.value(patient, GK.age))
    risks = sorted(str(r).split("#")[1] for r in g.objects(patient, GK.hasRiskFactor))
    meds = sorted(
        [
            {"id": str(m).split("#")[1], "regular": (patient, GK.takesRegularly, m) in g}
            for m in set(g.objects(patient, GK.takesRegularly)) | set(g.objects(patient, GK.takesMedication))
        ],
        key=lambda x: x["id"],
    )
    symptoms = []
    for obs in g.objects(enc, GK.hasObservation):
        s = g.value(obs, GK.observedSymptom)
        answer = "yes"
        if s is None:
            s = g.value(obs, GK.deniedSymptom)
            answer = "no"
        cf = float(g.value(obs, GK.userCF))
        symptoms.append({"id": str(s).split("#")[1], "answer": answer, "certainty": round(cf, 1)})
    symptoms.sort(key=lambda x: x["id"])
    return {
        "age": age,
        "riskFactors": risks,
        "medications": meds,
        "symptoms": symptoms,
        "disabledRules": [],
        "extraKnowledge": None,
    }
