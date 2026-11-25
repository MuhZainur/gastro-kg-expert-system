"""Build patient and encounter RDF triples strictly from rdflib terms."""
from __future__ import annotations

from uuid import uuid4

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD

from backend.app.engine import GK, GKD, PREFIXES
from backend.app.schemas import ConsultationRequest


def build_patient_graph(
    request: ConsultationRequest,
    *,
    patient_id: str | None = None,
    encounter_id: str | None = None,
    encounter_label: str | None = None,
) -> tuple[Graph, URIRef, URIRef]:
    token = uuid4().hex[:12]
    pid = patient_id or f"PQ{token}"
    eid = encounter_id or f"Q{token}"
    patient = GKD[pid]
    encounter = GKD[eid]

    graph = Graph()
    for prefix, namespace in PREFIXES.items():
        graph.bind(prefix, namespace)

    graph.add((patient, RDF.type, GK.Patient))
    graph.add((patient, RDFS.label, Literal(f"Patient ({request.age} y)", lang="en")))
    graph.add((patient, GK.age, Literal(request.age, datatype=XSD.integer)))
    graph.add((patient, GK.hadEncounter, encounter))

    for rf_id in request.riskFactors:
        graph.add((patient, GK.hasRiskFactor, GKD[rf_id]))

    for med in request.medications:
        pred = GK.takesRegularly if med.regular else GK.takesMedication
        graph.add((patient, pred, GKD[med.id]))

    graph.add((encounter, RDF.type, GK.Encounter))
    graph.add((encounter, RDFS.label, Literal(encounter_label or "Current screening encounter", lang="en")))

    for idx, sym in enumerate(request.symptoms, start=1):
        obs = GKD[f"{eid}_obs_{idx}_{sym.id}"]
        graph.add((encounter, GK.hasObservation, obs))
        graph.add((obs, RDF.type, GK.SymptomObservation))
        verb = "reports" if sym.answer == "yes" else "denies"
        graph.add((obs, RDFS.label, Literal(f"{verb} {sym.id} ({sym.certainty})", lang="en")))
        sym_pred = GK.observedSymptom if sym.answer == "yes" else GK.deniedSymptom
        graph.add((obs, sym_pred, GKD[sym.id]))
        graph.add((obs, GK.userCF, Literal(sym.certainty, datatype=XSD.decimal)))

    return graph, patient, encounter
