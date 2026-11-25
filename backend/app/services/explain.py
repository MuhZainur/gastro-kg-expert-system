"""Derive graph visualization payload and English provenance explanations."""
from __future__ import annotations

import re

from rdflib import Graph, Literal, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS

from backend.app.engine import GK, GKD, Rule
from backend.app.services.vocabulary import local_name

PROPERTY_TYPES = {
    OWL.ObjectProperty,
    OWL.DatatypeProperty,
    OWL.AnnotationProperty,
    OWL.FunctionalProperty,
    OWL.TransitiveProperty,
    RDF.Property,
}

KINDS = [
    ("Patient", "patient"),
    ("Encounter", "encounter"),
    ("Symptom", "symptom"),
    ("Disease", "disease"),
    ("Medication", "drug"),
    ("DrugClass", "drug"),
    ("TriageLevel", "triage"),
    ("CareFacility", "triage"),
    ("Hypothesis", "hypothesis"),
]


def short_term(term: URIRef) -> str:
    text = str(term)
    for namespace, prefix in (
        (str(GK), "gk:"),
        (str(GKD), "gkd:"),
        (str(RDFS), "rdfs:"),
        (str(RDF), "rdf:"),
    ):
        if text.startswith(namespace):
            return prefix + text[len(namespace):]
    return text


def is_ours(term: object) -> bool:
    return isinstance(term, URIRef) and str(term).startswith((str(GK), str(GKD)))


def _ancestors(tbox: Graph, cls: URIRef) -> set[URIRef]:
    found: set[URIRef] = set()
    todo: list[URIRef] = [cls]
    while todo:
        for parent in tbox.objects(todo.pop(), RDFS.subClassOf):
            if isinstance(parent, URIRef) and parent not in found:
                found.add(parent)
                todo.append(parent)
    return found


def explain_closure_triple(tbox: Graph, graph: Graph, s: URIRef, p: URIRef, o: URIRef) -> tuple[str, str]:
    """Return (origin 'd'|'o', English reason) for a triple added by RDFS/OWL 2 RL closure."""
    if p == RDF.type:
        if (o, OWL.equivalentClass, None) in tbox:
            return "o", f"owl:equivalentClass: {local_name(s)} satisfies the definition of {local_name(o)}"
        for union in tbox.subjects(RDFS.subClassOf, o):
            members = tbox.value(union, OWL.unionOf)
            if members is not None:
                for member in Collection(tbox, members):
                    if (s, RDF.type, member) in graph:
                        return "o", f"owl:unionOf: member {local_name(member)} belongs to {local_name(o)}"
        for child in tbox.subjects(RDFS.subClassOf, o):
            if isinstance(child, URIRef) and (s, RDF.type, child) in graph:
                return "d", f"rdfs:subClassOf: every {local_name(child)} is also {local_name(o)}"
        for q in sorted(set(graph.predicates(s, None)), key=str):
            if (q, RDFS.domain, o) in tbox:
                return "d", f"rdfs:domain: subject of {local_name(q)} is {local_name(o)}"
        for q in sorted(set(graph.predicates(None, s)), key=str):
            if (q, RDFS.range, o) in tbox:
                return "d", f"rdfs:range: object of {local_name(q)} is {local_name(o)}"
        for cls in sorted(graph.objects(s, RDF.type), key=str):
            if isinstance(cls, URIRef) and o in _ancestors(tbox, cls):
                return "d", f"rdfs:subClassOf chain: from {local_name(cls)} to {local_name(o)}"
        return "o", "Inferred by OWL 2 RL reasoner"

    if p == RDFS.subClassOf:
        if o in _ancestors(tbox, s):
            return "d", "rdfs:subClassOf chain (transitive)"
        return "o", "Derived from OWL class definition"

    for q in sorted(tbox.subjects(RDFS.subPropertyOf, p), key=str):
        if (s, q, o) in graph:
            return "d", f"rdfs:subPropertyOf: {local_name(q)} is a sub-property of {local_name(p)}"

    for q in sorted(set(tbox.objects(p, OWL.inverseOf)) | set(tbox.subjects(OWL.inverseOf, p)), key=str):
        if (o, q, s) in graph:
            return "o", f"owl:inverseOf: inverse of {local_name(q)}"

    for head in tbox.objects(p, OWL.propertyChainAxiom):
        chain = list(Collection(tbox, head))
        reached = {s}
        for step in chain:
            reached = {far for near in reached for far in graph.objects(near, step)}
        if o in reached:
            return "o", "owl:propertyChainAxiom: " + " then ".join(local_name(step) for step in chain)

    if (p, RDF.type, OWL.TransitiveProperty) in tbox:
        if any((middle, p, o) in graph for middle in graph.objects(s, p) if middle not in (s, o)):
            return "o", f"owl:TransitiveProperty: {local_name(p)} is transitive"

    return "o", "Inferred by OWL 2 RL reasoner"


def _snippet(tbox_text: str, term_short: str) -> str:
    blocks = []
    lines = tbox_text.splitlines()
    for i, line in enumerate(lines):
        starts = line.startswith(term_short + " ")
        union = line.startswith("[ a owl:Class ; owl:unionOf") and any(
            re.search(rf"rdfs:subClassOf {re.escape(term_short)}\b", following)
            for following in lines[i:i + 3]
        )
        if starts or union:
            block = []
            for following in lines[i:]:
                block.append(following)
                if re.search(r"\.\s*(#.*)?$", following):
                    break
            blocks.append("\n".join(block))
    return "\n\n".join(blocks)


def build_graph_payload(
    tbox: Graph,
    tbox_text: str,
    asserted: Graph,
    graph: Graph,
    rule_origins: dict[tuple, Rule],
    encounter: URIRef,
) -> dict:
    properties = {s for s, o in tbox.subject_objects(RDF.type) if o in PROPERTY_TYPES}
    classes = {s for s in tbox.subjects(RDF.type, OWL.Class) if is_ours(s)}

    reasons: list[str] = []
    reason_lookup: dict[str, int] = {}
    triples: list[list] = []

    def reason_idx(text: str) -> int:
        if text not in reason_lookup:
            reason_lookup[text] = len(reasons)
            reasons.append(text)
        return reason_lookup[text]

    for s, p, o in sorted(graph):
        if not (is_ours(s) and is_ours(o)) or s == o or s in properties or o in properties:
            continue
        if p not in (RDF.type, RDFS.subClassOf) and not str(p).startswith(str(GK)):
            continue
        triple = (s, p, o)
        if triple in asserted:
            origin, why = "f", "Asserted in knowledge base or patient input"
        elif triple in rule_origins:
            rule = rule_origins[triple]
            origin, why = "r", f"SPARQL rule {rule.name}: {rule.title}"
        else:
            origin, why = explain_closure_triple(tbox, graph, s, p, o)
        predicate = "type" if p == RDF.type else "subClassOf" if p == RDFS.subClassOf else local_name(p)
        triples.append([short_term(s), predicate, short_term(o), origin, reason_idx(why)])

    nodes: dict[str, list] = {}
    for term_short in sorted({t for s, _, o, _, _ in triples for t in (s, o)}):
        uri = URIRef(term_short.replace("gkd:", str(GKD), 1).replace("gk:", str(GK), 1))
        types = {local_name(t) for t in graph.objects(uri, RDF.type) if is_ours(t) and isinstance(t, URIRef)}
        kind = "class" if uri in classes else next((k for cls, k in KINDS if cls in types), "other")
        labels = {getattr(v, "language", None): str(v) for v in graph.objects(uri, RDFS.label)}
        values = sorted(
            [local_name(p), str(o)]
            for p, o in graph.predicate_objects(uri)
            if isinstance(o, Literal) and str(p).startswith(str(GK))
        )
        nodes[term_short] = [kind, labels.get("en") or labels.get(None) or "", labels.get("id", ""), values[:10]]

    axioms: dict[str, str] = {}
    for term_uri in sorted(classes | properties, key=str):
        if is_ours(term_uri):
            text = _snippet(tbox_text, short_term(term_uri))
            if text:
                key = local_name(term_uri) if term_uri in properties else short_term(term_uri)
                axioms[key] = text

    return {
        "focus": short_term(encounter),
        "nodes": nodes,
        "triples": triples,
        "reasons": reasons,
        "axioms": axioms,
    }
