"""Reason over every synthetic case and print a summary."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.app import engine  # noqa: E402

conforms, report = engine.shacl_report(engine.load_graph(engine.KNOWLEDGE, engine.CASES))
print("SHACL conforms:", conforms)
if not conforms:
    print(report)

result = engine.reason_all_cases()
print(f"asserted={result.asserted_count} after_owl={result.closure_count} rule_triples={len(result.inferred)}")
for name, count in result.rule_counts.items():
    print(f"  {name:32s} {count:5d}  {result.timings[name]:.2f}s")
print(f"  owl-rl closure {result.timings['owl-rl-closure']:.2f}s")

QUERY = """
SELECT ?e ?final ?d ?rank ?cf ?status WHERE {
  ?enc a gk:Encounter ; gk:finalTriage ?f .
  BIND(STRAFTER(STR(?enc), "#") AS ?e) BIND(STRAFTER(STR(?f), "#") AS ?final)
  OPTIONAL { ?h a gk:Hypothesis ; gk:ofEncounter ?enc ; gk:forDisease ?dis ; gk:rank ?rank ;
                gk:certaintyFactor ?cf ; gk:matchStatus ?s . FILTER(?rank <= 3)
             BIND(STRAFTER(STR(?dis), "#") AS ?d) BIND(STRAFTER(STR(?s), "#") AS ?status) }
} ORDER BY ?e ?rank
"""
current = None
for row in result.graph.query(QUERY, initNs=engine.PREFIXES):
    if row.e != current:
        current = row.e
        print(f"\n{row.e}  triage={row.final}")
    if row.d:
        print(f"    #{row.rank} {row.d:14s} CF={float(row.cf):.6f}  {row.status}")

for title, query in {
    "alerts": "SELECT ?l ?x WHERE { ?a a gk:SafetyAlert ; rdfs:label ?l ; gk:severity ?x } ORDER BY ?l",
    "best questions": "SELECT ?l ?x WHERE { ?q a gk:QuestionSuggestion ; gk:rank 1 ; rdfs:label ?l ; "
                      "gk:discriminationScore ?x } ORDER BY ?l",
    "recommendations": "SELECT ?l ?x WHERE { ?r a gk:Recommendation ; rdfs:label ?l . "
                       "OPTIONAL { ?r gk:recommendsExamination ?x } } ORDER BY ?l",
}.items():
    print(f"\n== {title}")
    for row in result.graph.query(query, initNs=engine.PREFIXES):
        print("   ", row[0], "|", str(row[1]).split("#")[-1])
