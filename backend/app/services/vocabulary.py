"""Derive form vocabulary and allowed identifiers from the ontology."""
from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS, SKOS

from backend.app.engine import GK, GKD


def local_name(uri: URIRef) -> str:
    text = str(uri)
    return text.split("#", 1)[-1] if "#" in text else text.rsplit("/", 1)[-1]


def label_of(graph: Graph, node: URIRef, lang: str = "en") -> str:
    values = list(graph.objects(node, RDFS.label))
    for value in values:
        if getattr(value, "language", None) == lang:
            return str(value)
    return str(values[0]) if values else local_name(node)


@dataclass(frozen=True)
class Vocabulary:
    form_payload: dict
    symptom_ids: frozenset[str]
    risk_factor_ids: frozenset[str]
    medication_ids: frozenset[str]
    drug_class_ids: frozenset[str]
    disease_ids: frozenset[str]
    used_codes: frozenset[str]
    base_uris: frozenset[URIRef]


def build_vocabulary(base_graph: Graph) -> Vocabulary:
    warning: list[dict] = []
    dyspeptic: list[dict] = []
    reflux: list[dict] = []
    symptom_ids: set[str] = set()

    # Collect asserted symptom types directly from knowledge graph
    for sym in base_graph.subjects(GK.code, None):
        types = set(base_graph.objects(sym, RDF.type))
        if not (types & {GK.DyspepticSymptom, GK.RefluxSymptom, GK.AlarmSymptom, GK.EmergencySymptom, GK.BleedingSymptom}):
            continue
        sid = local_name(sym)
        symptom_ids.add(sid)
        code = str(base_graph.value(sym, GK.code))
        entry = {
            "id": sid,
            "code": code,
            "label": label_of(base_graph, sym, "en"),
            "labelId": label_of(base_graph, sym, "id"),
            "altLabels": sorted(str(v) for v in base_graph.objects(sym, SKOS.altLabel)),
        }
        if types & {GK.BleedingSymptom, GK.EmergencySymptom}:
            warning.append({**entry, "level": "emergency"})
        elif GK.AlarmSymptom in types:
            warning.append({**entry, "level": "alarm"})
        elif GK.DyspepticSymptom in types:
            dyspeptic.append(entry)
        elif GK.RefluxSymptom in types:
            reflux.append(entry)

    warning.sort(key=lambda item: item["code"])
    dyspeptic.sort(key=lambda item: item["code"])
    reflux.sort(key=lambda item: item["code"])

    risk_factors = []
    risk_ids: set[str] = set()
    for rf in base_graph.subjects(RDF.type, GK.RiskFactor):
        rid = local_name(rf)
        risk_ids.add(rid)
        risk_factors.append({
            "id": rid,
            "label": label_of(base_graph, rf, "en"),
            "labelId": label_of(base_graph, rf, "id"),
        })
    risk_factors.sort(key=lambda item: item["id"])

    medications = []
    medication_ids: set[str] = set()
    for med in base_graph.subjects(RDF.type, GK.Medication):
        mid = local_name(med)
        medication_ids.add(mid)
        dc = base_graph.value(med, GK.drugClass)
        medications.append({
            "id": mid,
            "label": label_of(base_graph, med, "en"),
            "drugClass": {"id": local_name(dc), "label": label_of(base_graph, dc, "en")},
        })
    medications.sort(key=lambda item: item["id"])

    drug_class_ids = frozenset(local_name(dc) for dc in base_graph.subjects(RDF.type, GK.DrugClass))
    disease_ids = frozenset(
        local_name(d) for d in base_graph.subjects(GK.code, None)
        if str(base_graph.value(d, GK.code)).startswith("P")
    )
    used_codes = frozenset(str(c) for c in base_graph.objects(None, GK.code))
    base_uris = frozenset(
        term for s, p, o in base_graph for term in (s, p, o) if isinstance(term, URIRef)
    )

    form_payload = {
        "symptomGroups": [
            {"id": "warning", "title": "Warning signs", "symptoms": warning},
            {"id": "dyspeptic", "title": "Stomach complaints", "symptoms": dyspeptic},
            {"id": "reflux", "title": "Reflux complaints", "symptoms": reflux},
        ],
        "riskFactors": risk_factors,
        "medications": medications,
    }

    return Vocabulary(
        form_payload=form_payload,
        symptom_ids=frozenset(symptom_ids),
        risk_factor_ids=frozenset(risk_ids),
        medication_ids=frozenset(medication_ids),
        drug_class_ids=drug_class_ids,
        disease_ids=disease_ids,
        used_codes=used_codes,
        base_uris=base_uris,
    )
