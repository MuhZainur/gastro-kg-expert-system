"""Build docs/gastrokg-graph.html: an expandable graph where every relation says where it comes from.

Origins: f = written in a .ttl file, d = RDFS entailment, o = OWL 2 entailment, r = SPARQL rule.
For each RDFS/OWL relation the premises are looked up in the graph, so the reason shown is real.
Run:  python scripts/make_graph.py
"""
import json
import re
import sys
from pathlib import Path

from rdflib import BNode, Literal, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend.app import engine  # noqa: E402
from backend.app.engine import GK, GKD  # noqa: E402


def short(term):
    text = str(term)
    for namespace, prefix in ((str(GK), "gk:"), (str(GKD), "gkd:"), (str(RDFS), "rdfs:"), (str(RDF), "rdf:")):
        if text.startswith(namespace):
            return prefix + text[len(namespace):]
    return text


def name(term):
    return short(term).split(":", 1)[-1]


def ours(term):
    return isinstance(term, URIRef) and str(term).startswith((str(GK), str(GKD)))


tbox = engine.load_graph(engine.TBOX)
asserted = engine.load_graph(engine.TBOX, engine.KNOWLEDGE, engine.CASES)
rules = engine.load_rules()
graph = engine.reason(asserted, disabled=frozenset(r.name for r in rules)).graph
rule_of = {}
for rule in rules:
    new, _, _ = engine.apply_rules(graph, [rule])
    for triple in new:
        rule_of[triple] = rule


def ancestors(cls):
    """Superclasses reachable through subClassOf statements written in the T-Box."""
    found, todo = set(), [cls]
    while todo:
        for parent in tbox.objects(todo.pop(), RDFS.subClassOf):
            if isinstance(parent, URIRef) and parent not in found:
                found.add(parent)
                todo.append(parent)
    return found


def explain(s, p, o):
    """(origin, reason) for a triple the OWL 2 RL closure added, or None if no premise is found."""
    if p == RDF.type:
        if (o, OWL.equivalentClass, None) in tbox:
            return "o", f"owl:equivalentClass: {name(s)} memenuhi definisi kelas {name(o)}"
        for union in tbox.subjects(RDFS.subClassOf, o):
            members = tbox.value(union, OWL.unionOf)
            if members is not None:
                for member in Collection(tbox, members):
                    if (s, RDF.type, member) in graph:
                        return "o", f"owl:unionOf: anggota {name(member)} termasuk {name(o)}"
        for child in tbox.subjects(RDFS.subClassOf, o):
            if isinstance(child, URIRef) and (s, RDF.type, child) in graph:
                return "d", f"rdfs:subClassOf: setiap {name(child)} juga {name(o)}"
        for q in sorted(set(graph.predicates(s, None))):
            if (q, RDFS.domain, o) in tbox:
                return "d", f"rdfs:domain: subjek {name(q)} adalah {name(o)}"
        for q in sorted(set(graph.predicates(None, s))):
            if (q, RDFS.range, o) in tbox:
                return "d", f"rdfs:range: objek {name(q)} adalah {name(o)}"
        for cls in sorted(graph.objects(s, RDF.type)):
            if o in ancestors(cls):
                return "d", f"rdfs:subClassOf berantai: dari {name(cls)} ke {name(o)}"
        return None
    if p == RDFS.subClassOf:
        if o in ancestors(s):
            return "d", "rdfs:subClassOf berantai (transitif)"
        return "o", "diturunkan dari definisi kelas OWL"
    for q in tbox.subjects(RDFS.subPropertyOf, p):
        if (s, q, o) in graph:
            return "d", f"rdfs:subPropertyOf: {name(q)} adalah turunan {name(p)}"
    for q in set(tbox.objects(p, OWL.inverseOf)) | set(tbox.subjects(OWL.inverseOf, p)):
        if (o, q, s) in graph:
            return "o", f"owl:inverseOf: kebalikan dari {name(q)}"
    for head in tbox.objects(p, OWL.propertyChainAxiom):
        chain = list(Collection(tbox, head))
        reached = {s}
        for step in chain:
            reached = {far for near in reached for far in graph.objects(near, step)}
        if o in reached:
            return "o", "owl:propertyChainAxiom: " + " lalu ".join(name(step) for step in chain)
    if (p, RDF.type, OWL.TransitiveProperty) in tbox:
        if any((middle, p, o) in graph for middle in graph.objects(s, p) if middle not in (s, o)):
            return "o", f"owl:TransitiveProperty: {name(p)} diteruskan"
    return None


PROPERTY_TYPES = {OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty, OWL.FunctionalProperty,
                  OWL.TransitiveProperty, RDF.Property}
properties = {s for s, o in tbox.subject_objects(RDF.type) if o in PROPERTY_TYPES}
classes = {s for s in tbox.subjects(RDF.type, OWL.Class) if ours(s)}

reasons, triples, unexplained = [], [], []


def reason_index(text):
    if text not in reasons:
        reasons.append(text)
    return reasons.index(text)


for s, p, o in sorted(graph):
    if not (ours(s) and ours(o)) or s == o or s in properties or o in properties:
        continue
    if p not in (RDF.type, RDFS.subClassOf) and not str(p).startswith(str(GK)):
        continue
    if (s, p, o) in asserted:
        origin, why = "f", "Ditulis langsung di file .ttl"
    elif (s, p, o) in rule_of:
        rule = rule_of[(s, p, o)]
        origin, why = "r", f"Rule SPARQL {rule.name}: {rule.title}"
    else:
        found = explain(s, p, o)
        if found is None:
            unexplained.append((short(s), short(p), short(o)))
            found = "o", "Kesimpulan reasoner OWL 2 RL"
        origin, why = found
    predicate = "type" if p == RDF.type else "subClassOf" if p == RDFS.subClassOf else name(p)
    triples.append([short(s), predicate, short(o), origin, reason_index(why)])

KINDS = [("Patient", "patient"), ("Encounter", "encounter"), ("Symptom", "symptom"), ("Disease", "disease"),
         ("Medication", "drug"), ("DrugClass", "drug"), ("TriageLevel", "triage"), ("CareFacility", "triage"),
         ("Hypothesis", "hypothesis")]
nodes = {}
for term in sorted({t for s, _, o, _, _ in triples for t in (s, o)}):
    uri = URIRef(term.replace("gkd:", str(GKD)).replace("gk:", str(GK)))
    types = {name(t) for t in graph.objects(uri, RDF.type) if ours(t)}
    kind = "class" if uri in classes else next((k for cls, k in KINDS if cls in types), "other")
    labels = {getattr(v, "language", None): str(v) for v in graph.objects(uri, RDFS.label)}
    values = sorted([name(p), str(o)] for p, o in graph.predicate_objects(uri)
                    if isinstance(o, Literal) and str(p).startswith(str(GK)))
    nodes[term] = [kind, labels.get("en") or labels.get(None) or "", labels.get("id", ""), values[:10]]

source = engine.TBOX.read_text(encoding="utf-8")


def snippet(term):
    """The Turtle statement(s) about a term, copied from the T-Box file."""
    blocks = []
    lines = source.splitlines()
    for i, line in enumerate(lines):
        starts = line.startswith(term + " ")
        union = line.startswith("[ a owl:Class ; owl:unionOf") and any(
            re.search(rf"rdfs:subClassOf {term}\b", following) for following in lines[i:i + 3])
        if starts or union:
            block = []
            for following in lines[i:]:
                block.append(following)
                if re.search(r"\.\s*(#.*)?$", following):
                    break
            blocks.append("\n".join(block))
    return "\n\n".join(blocks)


axioms = {}
for term in classes | properties:
    if ours(term):
        text = snippet(short(term))
        if text:
            axioms[name(term) if term in properties else short(term)] = text

data = {"nodes": nodes, "triples": triples, "reasons": reasons, "axioms": axioms}
template = (ROOT / "docs" / "graph.template.html").read_text(encoding="utf-8")
assert "/*__DATA__*/null" in template
payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
out = ROOT / "docs" / "gastrokg-graph.html"
out.write_text(template.replace("/*__DATA__*/null", payload), encoding="utf-8")
count = {key: sum(t[3] == key for t in triples) for key in "fdor"}
print(f"{out.name}: {out.stat().st_size / 1024:.0f} KB, {len(nodes)} nodes, relations by origin {count}")
print(f"relations without a found premise: {len(unexplained)} {unexplained[:8]}")
