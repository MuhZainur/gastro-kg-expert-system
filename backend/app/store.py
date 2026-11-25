"""Read-only knowledge store loaded once at startup, with reasoning lock."""
from __future__ import annotations

import threading
from functools import lru_cache

import rdflib.plugins.sparql as sparql_mod
from rdflib import Graph

from backend.app import engine
from backend.app.engine import PREFIXES, Rule
from backend.app.services.vocabulary import Vocabulary, build_vocabulary

RULE_GROUPS: list[tuple[str, list[str]]] = [
    ("Knowledge enrichment", ["01"]),
    ("Forward chaining", ["10", "40", "41"]),
    ("Certainty factor", ["20", "21", "22", "30"]),
    ("Status and ranking", ["42", "43", "44", "45", "50", "51"]),
    ("Context and medication safety", ["60", "61", "62"]),
    ("Triage", ["70", "71", "72", "73", "74", "75", "76"]),
    ("Recommendations", ["90", "91", "92"]),
    ("Backward chaining", ["46", "95", "96"]),
]


def _rule_group(name: str) -> str:
    prefix = name[:2]
    for title, codes in RULE_GROUPS:
        if prefix in codes:
            return title
    return "Other"


class KnowledgeStore:
    def __init__(self) -> None:
        sparql_mod.SPARQL_LOAD_GRAPHS = False
        self.lock = threading.Lock()
        self.tbox_graph = engine.load_graph(engine.TBOX)
        self.shapes_graph = engine.load_graph(engine.SHAPES)
        self.base_graph = engine.load_graph(engine.TBOX, engine.KNOWLEDGE)
        self.rules: list[Rule] = engine.load_rules()
        self.rule_names: frozenset[str] = frozenset(rule.name for rule in self.rules)
        self.rules_payload: dict = {
            "rules": [
                {
                    "name": rule.name,
                    "group": _rule_group(rule.name),
                    "title": rule.title,
                    "description": rule.description,
                    "iterate": rule.iterate,
                    "query": rule.query,
                }
                for rule in self.rules
            ]
        }
        self.vocabulary: Vocabulary = build_vocabulary(self.base_graph)
        self.tbox_text: str = engine.TBOX.read_text(encoding="utf-8")

    def copy_base(self) -> Graph:
        graph = Graph()
        for prefix, namespace in PREFIXES.items():
            graph.bind(prefix, namespace)
        for triple in self.base_graph:
            graph.add(triple)
        return graph


@lru_cache(maxsize=1)
def get_store() -> KnowledgeStore:
    return KnowledgeStore()
