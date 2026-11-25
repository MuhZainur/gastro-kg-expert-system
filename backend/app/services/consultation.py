"""Run validation, reasoning, and assemble the consultation response."""
from __future__ import annotations

import time
from decimal import Decimal

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, RDF

from backend.app import engine
from backend.app.config import DISCLAIMER
from backend.app.engine import GK, GKD, Rule
from backend.app.schemas import ConsultationRequest
from backend.app.services.custom import CustomKnowledgeError, parse_and_validate_custom_knowledge
from backend.app.services.explain import build_graph_payload, explain_closure_triple
from backend.app.services.facts import build_patient_graph
from backend.app.services.vocabulary import label_of, local_name
from backend.app.store import KnowledgeStore

WATCHED_OWL_TYPES = frozenset({
    "EmergencyEncounter",
    "AlarmEncounter",
    "DyspepticEncounter",
    "NSAIDUser",
    "AnticoagulantUser",
    "HPyloriHistoryPatient",
    "UlcerRiskPatient",
})


class RequestValidationProblem(ValueError):
    def __init__(self, code: str, field: str | None, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.field = field
        self.message = message


def _clean_text(text: str, encounter_id: str, patient_id: str) -> str:
    cleaned = text.replace(f"{encounter_id} ", "").replace(encounter_id, "current encounter")
    cleaned = cleaned.replace(f"{patient_id} ", "").replace(patient_id, "patient")
    return cleaned.strip()


def _val_num(graph: Graph, subject: URIRef, predicate: URIRef) -> float | None:
    val = graph.value(subject, predicate)
    if val is None:
        return None
    if isinstance(val, Literal):
        py = val.toPython()
        return float(py) if isinstance(py, (int, float, Decimal)) else None
    return None


def _source_text(graph: Graph, source_node: object) -> str:
    if isinstance(source_node, URIRef):
        s = str(source_node)
        if s.startswith("https://"):
            return s
        return label_of(graph, source_node, "en")
    return str(source_node)


def run_consultation(
    store: KnowledgeStore,
    request: ConsultationRequest,
    *,
    patient_id: str | None = None,
    encounter_id: str | None = None,
    encounter_label: str | None = None,
    precomputed: bool = False,
) -> dict:
    vocab = store.vocabulary

    for idx, sym in enumerate(request.symptoms):
        if sym.id not in vocab.symptom_ids:
            raise RequestValidationProblem("validation", f"symptoms.{idx}.id", "Unknown symptom.")

    for idx, rf_id in enumerate(request.riskFactors):
        if rf_id not in vocab.risk_factor_ids:
            raise RequestValidationProblem("validation", f"riskFactors.{idx}", "Unknown risk factor.")

    for idx, rule_name in enumerate(request.disabledRules):
        if rule_name not in store.rule_names:
            raise RequestValidationProblem("validation", f"disabledRules.{idx}", "Unknown rule name.")

    custom_graph: Graph | None = None
    custom_meds: frozenset[str] = frozenset()
    if request.extraKnowledge is not None and request.extraKnowledge.strip():
        try:
            custom_graph, custom_meds = parse_and_validate_custom_knowledge(request.extraKnowledge, vocab)
        except CustomKnowledgeError as exc:
            raise RequestValidationProblem("custom_knowledge", "extraKnowledge", str(exc)) from exc

    allowed_meds = vocab.medication_ids | custom_meds
    for idx, med in enumerate(request.medications):
        if med.id not in allowed_meds:
            raise RequestValidationProblem("validation", f"medications.{idx}.id", "Unknown medication.")

    total_started = time.perf_counter()
    with store.lock:
        patient_graph, patient, encounter = build_patient_graph(
            request,
            patient_id=patient_id,
            encounter_id=encounter_id,
            encounter_label=encounter_label,
        )
        asserted = store.copy_base()
        for triple in patient_graph:
            asserted.add(triple)
        if custom_graph is not None:
            for triple in custom_graph:
                asserted.add(triple)

        shacl_started = time.perf_counter()
        conforms, report_text = engine.shacl_report(
            asserted, shacl_graph=store.shapes_graph, ont_graph=store.tbox_graph
        )
        shacl_seconds = time.perf_counter() - shacl_started
        if not conforms:
            messages = _extract_shacl_messages(report_text)
            raise RequestValidationProblem("shacl", None, messages)

        disabled = frozenset(request.disabledRules)
        rule_origins: dict[tuple, Rule] = {}
        result = engine.reason(asserted, disabled=disabled, rules=store.rules, origins=rule_origins)

    total_seconds = time.perf_counter() - total_started
    closure_seconds = result.timings.get("owl-rl-closure", 0.0)
    rules_seconds = sum(v for k, v in result.timings.items() if k != "owl-rl-closure")

    payload = _collect_response(
        store=store,
        asserted=asserted,
        graph=result.graph,
        rule_origins=rule_origins,
        patient=patient,
        encounter=encounter,
        asserted_count=result.asserted_count,
        closure_count=result.closure_count,
        inferred_count=len(result.inferred),
        shacl_seconds=shacl_seconds,
        closure_seconds=closure_seconds,
        rules_seconds=rules_seconds,
        total_seconds=total_seconds,
        disabled_rules=list(request.disabledRules),
        custom_knowledge=custom_graph is not None and len(custom_graph) > 0,
        precomputed=precomputed,
    )
    return payload


def _extract_shacl_messages(report_text: str) -> str:
    lines = [
        line.split(":", 1)[1].strip()
        for line in report_text.splitlines()
        if line.strip().startswith("Message:")
    ]
    if lines:
        return "; ".join(dict.fromkeys(lines))
    return "Input data did not satisfy ontology validation constraints."


def _collect_response(
    *,
    store: KnowledgeStore,
    asserted: Graph,
    graph: Graph,
    rule_origins: dict[tuple, Rule],
    patient: URIRef,
    encounter: URIRef,
    asserted_count: int,
    closure_count: int,
    inferred_count: int,
    shacl_seconds: float,
    closure_seconds: float,
    rules_seconds: float,
    total_seconds: float,
    disabled_rules: list[str],
    custom_knowledge: bool,
    precomputed: bool,
) -> dict:
    eid = local_name(encounter)
    pid = local_name(patient)

    def of_type(cls: URIRef) -> list[URIRef]:
        return sorted(
            (s for s in graph.subjects(GK.ofEncounter, encounter) if (s, RDF.type, cls) in graph),
            key=str,
        )

    # Triage
    decisions = []
    for d in of_type(GK.TriageDecision):
        level = graph.value(d, GK.triageLevel)
        if not isinstance(level, URIRef):
            continue
        prio_lit = graph.value(level, GK.priority)
        priority = int(prio_lit.toPython()) if isinstance(prio_lit, Literal) else 0
        triggered = sorted(
            _clean_text(label_of(graph, x, "en"), eid, pid) if isinstance(x, URIRef) else str(x)
            for x in graph.objects(d, GK.triggeredBy)
        )
        decisions.append({
            "priority": priority,
            "level": local_name(level),
            "reason": str(graph.value(d, GK.reason) or ""),
            "triggeredBy": triggered,
        })
    decisions.sort(key=lambda item: (-item["priority"], item["level"], item["reason"]))

    final = graph.value(encounter, GK.finalTriage)
    if isinstance(final, URIRef):
        place = graph.value(final, GK.refersTo)
        triage = {
            "level": local_name(final),
            "label": label_of(graph, final, "en"),
            "labelId": label_of(graph, final, "id"),
            "facility": label_of(graph, place, "en") if isinstance(place, URIRef) else "",
            "reasons": [
                {"level": d["level"], "reason": d["reason"], "triggeredBy": d["triggeredBy"]}
                for d in decisions
            ],
        }
    else:
        triage = None

    # Hypotheses
    hypotheses = []
    for h in graph.subjects(GK.ofEncounter, encounter):
        if (h, RDF.type, GK.Hypothesis) not in graph:
            continue
        disease = graph.value(h, GK.forDisease)
        if not isinstance(disease, URIRef):
            continue
        steps = []
        for item in graph.subjects(GK.ofHypothesis, h):
            link = graph.value(item, GK.basedOnLink)
            obs = graph.value(item, GK.basedOnObservation)
            if not (isinstance(link, URIRef) and isinstance(obs, URIRef)):
                continue
            symptom = graph.value(link, GK.aboutSymptom)
            if not isinstance(symptom, URIRef):
                continue
            denied = (obs, GK.deniedSymptom, symptom) in graph
            polarity = "oppose" if graph.value(item, GK.polarity) == GKD.Oppose else "support"
            seq_lit = graph.value(item, GK.sequence)
            steps.append({
                "seq": int(seq_lit.toPython()) if isinstance(seq_lit, Literal) else 0,
                "polarity": polarity,
                "denied": denied,
                "symptom": {
                    "id": local_name(symptom),
                    "code": str(graph.value(symptom, GK.code) or ""),
                    "label": label_of(graph, symptom, "en"),
                    "labelId": label_of(graph, symptom, "id"),
                },
                "patientCertainty": _val_num(graph, obs, GK.userCF) or 0.0,
                "expertWeight": _val_num(graph, link, GK.absenceCF if denied else GK.expertCF) or 0.0,
                "itemCf": _val_num(graph, item, GK.itemCF) or 0.0,
                "before": _val_num(graph, item, GK.cumulativeBefore) or 0.0,
                "after": _val_num(graph, item, GK.cumulativeAfter) or 0.0,
                "sources": sorted(_source_text(graph, s) for s in graph.objects(link, DCTERMS.source)),
            })
        steps.sort(key=lambda s: (s["polarity"] == "oppose", s["seq"]))

        missing = [
            {
                "id": local_name(s),
                "code": str(graph.value(s, GK.code) or ""),
                "label": label_of(graph, s, "en"),
                "labelId": label_of(graph, s, "id"),
            }
            for s in graph.objects(h, GK.missingSymptom)
            if isinstance(s, URIRef)
        ]
        missing.sort(key=lambda item: item["code"])

        risk_factors = [
            {
                "id": local_name(r),
                "label": label_of(graph, r, "en"),
                "labelId": label_of(graph, r, "id"),
            }
            for r in graph.objects(h, GK.contextRiskFactor)
            if isinstance(r, URIRef)
        ]
        risk_factors.sort(key=lambda item: item["id"])

        rank_lit = graph.value(h, GK.rank)
        status_node = graph.value(h, GK.matchStatus)
        hypotheses.append({
            "disease": {"id": local_name(disease), "label": label_of(graph, disease, "en")},
            "code": str(graph.value(disease, GK.code) or ""),
            "rank": int(rank_lit.toPython()) if isinstance(rank_lit, Literal) else 999,
            "status": local_name(status_node) if isinstance(status_node, URIRef) else "WeakMatch",
            "cf": _val_num(graph, h, GK.certaintyFactor) or 0.0,
            "support": _val_num(graph, h, GK.supportCF) or 0.0,
            "opposition": _val_num(graph, h, GK.oppositionCF) or 0.0,
            "coverage": _val_num(graph, h, GK.ruleCoverage) or 0.0,
            "steps": steps,
            "missing": missing,
            "riskFactors": risk_factors,
            "advice": str(graph.value(disease, GK.initialAdvice) or ""),
        })
    hypotheses.sort(key=lambda h: (h["rank"], h["code"]))

    # Rule matches
    reported = set()
    for obs in graph.objects(encounter, GK.hasObservation):
        sym = graph.value(obs, GK.observedSymptom)
        if isinstance(sym, URIRef):
            reported.add(sym)

    rule_matches = []
    for m in of_type(GK.RuleMatch):
        rule_node = graph.value(m, GK.firedRule) or graph.value(m, GK.evaluatesRule)
        disease = graph.value(m, GK.forDisease)
        if not (isinstance(rule_node, URIRef) and isinstance(disease, URIRef)):
            continue
        matched = int(graph.value(m, GK.matchedCount).toPython())
        required = int(graph.value(m, GK.requiredCount).toPython())
        conditions = [
            {
                "code": str(graph.value(s, GK.code) or ""),
                "label": label_of(graph, s, "en"),
                "met": s in reported,
            }
            for s in graph.objects(rule_node, GK.requiresSymptom)
            if isinstance(s, URIRef)
        ]
        conditions.sort(key=lambda c: c["code"])
        rule_matches.append({
            "rule": local_name(rule_node),
            "disease": {"id": local_name(disease), "label": label_of(graph, disease, "en")},
            "matched": matched,
            "required": required,
            "fired": (m, RDF.type, GK.RuleFiring) in graph,
            "conditions": conditions,
        })
    rule_matches.sort(key=lambda m: (not m["fired"], -m["matched"] / max(m["required"], 1), m["rule"]))

    # OWL / RDFS facts on encounter and patient
    owl_facts = []
    for node, subj_label in ((encounter, "Current encounter"), (patient, "Patient")):
        for p, o in graph.predicate_objects(node):
            if not isinstance(o, URIRef):
                continue
            triple = (node, p, o)
            if triple in asserted or triple in rule_origins:
                continue
            if (p == RDF.type and local_name(o) in WATCHED_OWL_TYPES) or p in (
                GK.showsSymptom,
                GK.takesDrugClass,
                GK.encounterOf,
            ):
                _origin, why = explain_closure_triple(store.tbox_graph, graph, node, p, o)
                owl_facts.append({
                    "subject": {"id": local_name(node), "label": subj_label},
                    "relation": "type" if p == RDF.type else local_name(p),
                    "value": {
                        "id": local_name(o),
                        "label": "Current encounter" if o == encounter else "Patient" if o == patient else label_of(graph, o, "en"),
                    },
                    "reason": _clean_text(why, eid, pid),
                })
    owl_facts.sort(key=lambda f: (f["subject"]["id"], f["relation"], f["value"]["id"]))

    # Medication alerts
    alerts = []
    for a in of_type(GK.SafetyAlert):
        meds = sorted(
            ({"id": local_name(m), "label": label_of(graph, m, "en")}
             for m in graph.objects(a, GK.concernsMedication) if isinstance(m, URIRef)),
            key=lambda x: x["id"],
        )
        disease = graph.value(a, GK.forDisease)
        alts = sorted(
            ({"id": local_name(x), "label": label_of(graph, x, "en")}
             for x in graph.objects(a, GK.suggestedAlternative) if isinstance(x, URIRef)),
            key=lambda x: x["id"],
        )
        alerts.append({
            "medicines": meds,
            "disease": {"id": local_name(disease), "label": label_of(graph, disease, "en")} if isinstance(disease, URIRef) else None,
            "severity": str(graph.value(a, GK.severity) or ""),
            "reason": str(graph.value(a, GK.reason) or ""),
            "alternatives": alts,
        })
    alerts.sort(
        key=lambda a: (
            0 if a["severity"] == "high" else 1,
            a["disease"]["id"] if a["disease"] else "",
            ",".join(m["id"] for m in a["medicines"]),
        )
    )

    # Recommendations
    recommendations = []
    for r in of_type(GK.Recommendation):
        exams = sorted(
            label_of(graph, x, "en")
            for x in graph.objects(r, GK.recommendsExamination)
            if isinstance(x, URIRef)
        )
        recommendations.append({
            "text": str(graph.value(r, GK.adviceText) or ""),
            "examinations": exams,
        })
    recommendations.sort(key=lambda item: item["text"])

    # Next question
    next_question = None
    for q in of_type(GK.QuestionSuggestion):
        if (q, GK.rank, Literal(1)) in graph or (q, GK.rank, None) in graph:
            sym = graph.value(q, GK.askSymptom)
            if isinstance(sym, URIRef):
                next_question = {
                    "id": local_name(sym),
                    "code": str(graph.value(sym, GK.code) or ""),
                    "label": label_of(graph, sym, "en"),
                    "labelId": label_of(graph, sym, "id"),
                    "score": _val_num(graph, q, GK.discriminationScore) or 0.0,
                }
                break

    graph_payload = build_graph_payload(
        tbox=store.tbox_graph,
        tbox_text=store.tbox_text,
        asserted=asserted,
        graph=graph,
        rule_origins=rule_origins,
        encounter=encounter,
    )

    seconds = (
        None
        if precomputed
        else {
            "shacl": round(shacl_seconds, 4),
            "closure": round(closure_seconds, 4),
            "rules": round(rules_seconds, 4),
            "total": round(total_seconds, 4),
        }
    )

    return {
        "triage": triage,
        "hypotheses": hypotheses,
        "ruleMatches": rule_matches,
        "owlFacts": owl_facts,
        "alerts": alerts,
        "recommendations": recommendations,
        "nextQuestion": next_question,
        "graph": graph_payload,
        "meta": {
            "asserted": asserted_count,
            "afterClosure": closure_count,
            "inferred": inferred_count,
            "precomputed": precomputed,
            "seconds": seconds,
            "disabledRules": disabled_rules,
            "customKnowledge": custom_knowledge,
        },
        "disclaimer": DISCLAIMER,
    }
