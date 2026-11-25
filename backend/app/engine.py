"""GastroKG inference engine.

Pipeline: SHACL validation -> OWL 2 RL closure (includes the RDFS patterns) ->
SPARQL CONSTRUCT rules, run in file-name order, into a separate inferred graph.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import owlrl
from pyshacl import validate
from rdflib import Graph, Namespace

ROOT = Path(__file__).resolve().parents[2]
GK = Namespace("http://example.org/gastrokg/ontology#")
GKD = Namespace("http://example.org/gastrokg/data#")
PREFIXES = {"gk": GK, "gkd": GKD}

TBOX = ROOT / "ontology" / "gastrokg-tbox.ttl"
KNOWLEDGE = ROOT / "ontology" / "gastrokg-knowledge.ttl"
CASES = ROOT / "ontology" / "gastrokg-cases.ttl"
SHAPES = ROOT / "shapes" / "gastrokg-shapes.ttl"
RULES_DIR = ROOT / "rules"


@dataclass(frozen=True)
class Rule:
    name: str
    title: str
    description: str
    iterate: bool
    query: str


@dataclass
class Result:
    graph: Graph                      # asserted + OWL closure + rule results
    inferred: Graph                   # rule results only
    asserted_count: int = 0
    closure_count: int = 0
    rule_counts: dict[str, int] = field(default_factory=dict)
    timings: dict[str, float] = field(default_factory=dict)


def load_rules(directory: Path = RULES_DIR) -> list[Rule]:
    rules = []
    for path in sorted(directory.glob("*.rq")):
        text = path.read_text(encoding="utf-8")
        meta = dict(
            line[2:].split(": ", 1) for line in text.splitlines() if line.startswith("# ") and ": " in line
        )
        rules.append(Rule(path.stem, meta["title"], meta["description"], meta["iterate"] == "true", text))
    return rules


def load_graph(*paths: Path) -> Graph:
    graph = Graph()
    for prefix, namespace in PREFIXES.items():
        graph.bind(prefix, namespace)
    for path in paths:
        graph.parse(path, format="turtle")
    return graph


def shacl_report(data: Graph, shacl_graph: Graph | None = None, ont_graph: Graph | None = None) -> tuple[bool, str]:
    """Validate asserted data against the shapes, using the T-Box for sub-classes."""
    conforms, _, text = validate(
        data,
        shacl_graph=shacl_graph if shacl_graph is not None else load_graph(SHAPES),
        ont_graph=ont_graph if ont_graph is not None else load_graph(TBOX),
        advanced=True,
        inference="none",
    )
    return conforms, text


def apply_rules(
    graph: Graph,
    rules: list[Rule],
    disabled: frozenset[str] = frozenset(),
    origins: dict[tuple, Rule] | None = None,
):
    """Run the rules over `graph` (modified in place) and return (new triples, counts, timings)."""
    inferred = Graph()
    for prefix, namespace in PREFIXES.items():
        inferred.bind(prefix, namespace)
    counts, timings = {}, {}
    for rule in rules:
        if rule.name in disabled:
            continue
        started = time.perf_counter()
        added = 0
        while True:
            new = [triple for triple in graph.query(rule.query) if triple not in graph]
            for triple in new:
                graph.add(triple)
                inferred.add(triple)
                if origins is not None and triple not in origins:
                    origins[triple] = rule
            added += len(new)
            if not (rule.iterate and new):
                break
        counts[rule.name] = added
        timings[rule.name] = time.perf_counter() - started
    return inferred, counts, timings


def reason(
    asserted: Graph,
    disabled: frozenset[str] = frozenset(),
    rules: list[Rule] | None = None,
    origins: dict[tuple, Rule] | None = None,
) -> Result:
    graph = Graph()
    for prefix, namespace in PREFIXES.items():
        graph.bind(prefix, namespace)
    graph += asserted
    asserted_count = len(graph)

    started = time.perf_counter()
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics, axiomatic_triples=False, datatype_axioms=False).expand(graph)
    closure_seconds = time.perf_counter() - started
    closure_count = len(graph)

    inferred, counts, timings = apply_rules(graph, rules or load_rules(), disabled, origins=origins)
    timings = {"owl-rl-closure": closure_seconds, **timings}
    return Result(graph, inferred, asserted_count, closure_count, counts, timings)


def reason_all_cases() -> Result:
    return reason(load_graph(TBOX, KNOWLEDGE, CASES))
