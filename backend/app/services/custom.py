"""Allow-list validation for custom Turtle knowledge snippets."""
from __future__ import annotations

import re

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, RDF, RDFS

from backend.app.config import MAX_EXTRA_BYTES, MAX_EXTRA_TRIPLES, MAX_LITERAL_LEN
from backend.app.engine import GK, GKD
from backend.app.services.vocabulary import Vocabulary, local_name

LOCAL_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,40}$")
RULE_CODE_RE = re.compile(r"^R[0-9]{1,3}$")

ALLOWED_PREDICATES = frozenset({
    RDF.type,
    RDFS.label,
    GK.drugClass,
    GK.code,
    GK.concludes,
    GK.requiresSymptom,
    DCTERMS.source,
})
ALLOWED_TYPES = frozenset({GK.Medication, GK.DiagnosticRule})


class CustomKnowledgeError(ValueError):
    """Raised when extraKnowledge violates format, size, or allow-list rules."""


def parse_and_validate_custom_knowledge(turtle: str, vocab: Vocabulary) -> tuple[Graph, frozenset[str]]:
    raw_bytes = turtle.encode("utf-8")
    if len(raw_bytes) > MAX_EXTRA_BYTES:
        raise CustomKnowledgeError(f"Custom knowledge exceeds {MAX_EXTRA_BYTES} bytes.")

    graph = Graph()
    try:
        graph.parse(data=turtle, format="turtle")
    except Exception as exc:
        raise CustomKnowledgeError("Custom knowledge must be valid Turtle syntax.") from exc

    if len(graph) > MAX_EXTRA_TRIPLES:
        raise CustomKnowledgeError(f"Custom knowledge exceeds {MAX_EXTRA_TRIPLES} triples.")

    custom_meds: set[str] = set()
    seen_codes: set[str] = set()

    for s, p, o in graph:
        if isinstance(s, BNode) or isinstance(o, BNode):
            raise CustomKnowledgeError("Blank nodes are not allowed in custom knowledge.")

        if not isinstance(s, URIRef) or not str(s).startswith(str(GKD)):
            raise CustomKnowledgeError(f"Subject '{s}' must be in the gkd: data namespace.")

        s_local = local_name(s)
        if not LOCAL_NAME_RE.match(s_local):
            raise CustomKnowledgeError(f"Invalid subject local name '{s_local}'.")

        if s in vocab.base_uris:
            raise CustomKnowledgeError(f"Subject 'gkd:{s_local}' already exists and cannot be redefined.")

        if p not in ALLOWED_PREDICATES:
            raise CustomKnowledgeError(f"Predicate '{p}' is not allowed in custom knowledge.")

        if isinstance(o, Literal) and len(str(o)) > MAX_LITERAL_LEN:
            raise CustomKnowledgeError(f"Literal exceeds {MAX_LITERAL_LEN} characters.")

        if p == RDF.type:
            if o not in ALLOWED_TYPES:
                raise CustomKnowledgeError(f"Type '{o}' is not allowed; only gk:Medication and gk:DiagnosticRule are permitted.")
            if o == GK.Medication:
                custom_meds.add(s_local)
        elif p == RDFS.label:
            if not isinstance(o, Literal):
                raise CustomKnowledgeError("rdfs:label object must be a literal.")
        elif p == GK.drugClass:
            if not isinstance(o, URIRef) or not str(o).startswith(str(GKD)) or local_name(o) not in vocab.drug_class_ids:
                raise CustomKnowledgeError(f"Unknown drug class '{o}'.")
        elif p == GK.concludes:
            if not isinstance(o, URIRef) or not str(o).startswith(str(GKD)) or local_name(o) not in vocab.disease_ids:
                raise CustomKnowledgeError(f"Unknown disease '{o}'.")
        elif p == GK.requiresSymptom:
            if not isinstance(o, URIRef) or not str(o).startswith(str(GKD)) or local_name(o) not in vocab.symptom_ids:
                raise CustomKnowledgeError(f"Unknown symptom '{o}'.")
        elif p == DCTERMS.source:
            if o != GKD.GroupAssignment:
                raise CustomKnowledgeError("dcterms:source must be gkd:GroupAssignment.")
        elif p == GK.code:
            if not isinstance(o, Literal):
                raise CustomKnowledgeError("gk:code must be a literal.")
            code_val = str(o)
            if not RULE_CODE_RE.match(code_val):
                raise CustomKnowledgeError(f"Rule code '{code_val}' must match R followed by 1 to 3 digits.")
            if code_val in vocab.used_codes:
                raise CustomKnowledgeError(f"Rule code '{code_val}' is already in use.")
            seen_codes.add(code_val)

    return graph, frozenset(custom_meds)
