"""Set up GastroKG in a local GraphDB and check that it agrees with the Python engine.

  python scripts/graphdb_load.py            create the repository (if missing), load, run rules, compare
  python scripts/graphdb_load.py --url http://localhost:7200

Only the repository named "gastrokg" is touched. Its content is replaced on every run.
"""
import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend.app import engine  # noqa: E402

REPOSITORY = "gastrokg"
GRAPHS = {
    "urn:gastrokg:tbox": engine.TBOX,
    "urn:gastrokg:knowledge": engine.KNOWLEDGE,
    "urn:gastrokg:cases": engine.CASES,
}


def call(base, path, method="GET", body=None, headers=None):
    request = urllib.request.Request(base + path, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        raise SystemExit(f"{method} {path} -> HTTP {error.code}: {error.read().decode('utf-8')[:2000]}")


def ensure_repository(base):
    existing = [r["id"] for r in json.loads(call(base, "/rest/repositories", headers={"Accept": "application/json"}))]
    if REPOSITORY in existing:
        print(f"repository '{REPOSITORY}' already exists")
        return
    boundary = uuid.uuid4().hex
    config = (ROOT / "graphdb" / "repository-config.ttl").read_bytes()
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="config"; filename="config.ttl"\r\n'
            f"Content-Type: text/turtle\r\n\r\n").encode() + config + f"\r\n--{boundary}--\r\n".encode()
    call(base, "/rest/repositories", "POST", body, {"Content-Type": f"multipart/form-data; boundary={boundary}"})
    print(f"repository '{REPOSITORY}' created")


def update(base, text):
    call(base, f"/repositories/{REPOSITORY}/statements", "POST", text.encode("utf-8"),
         {"Content-Type": "application/sparql-update; charset=utf-8"})


def select(base, query):
    raw = call(base, f"/repositories/{REPOSITORY}", "POST",
               urllib.parse.urlencode({"query": query, "infer": "true"}).encode(),
               {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/sparql-results+json"})
    data = json.loads(raw)
    names = data["head"]["vars"]
    return [tuple(row.get(n, {}).get("value") for n in names) for row in data["results"]["bindings"]]


def inferred_size(base):
    return int(select(base, "SELECT (COUNT(*) AS ?n) WHERE { GRAPH <urn:gastrokg:inferred> { ?s ?p ?o } }")[0][0])


def run_rules(base):
    """One request (one commit) per rule, repeating the iterative ones until nothing changes."""
    for path in sorted((ROOT / "graphdb" / "updates").glob("*.ru")):
        text = path.read_text(encoding="utf-8")
        repeat = "# iterate: true" in text
        while True:
            before = inferred_size(base) if repeat else None
            update(base, text)
            if not repeat or inferred_size(base) == before:
                break
    return inferred_size(base)


def normal(value):
    """Compare numbers by value and everything else as text."""
    if value is None:
        return ""
    text = str(value)
    try:
        return format(Decimal(text).quantize(Decimal("1e-10")).normalize(), "f")
    except ArithmeticError:
        return text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:7200")
    base = parser.parse_args().url.rstrip("/")

    ensure_repository(base)
    update(base, "CLEAR ALL")
    for graph, path in GRAPHS.items():
        call(base, f"/repositories/{REPOSITORY}/rdf-graphs/service?graph={urllib.parse.quote(graph)}", "PUT",
             path.read_bytes(), {"Content-Type": "text/turtle; charset=utf-8"})
        print(f"loaded {path.name} into <{graph}>")
    # prefixes for the SPARQL editor and the search index used by Visual Graph
    for prefix, namespace in engine.PREFIXES.items():
        call(base, f"/repositories/{REPOSITORY}/namespaces/{prefix}", "PUT", str(namespace).encode(),
             {"Content-Type": "text/plain"})
    update(base, "INSERT DATA { _:s <http://www.ontotext.com/plugins/autocomplete#enabled> true }")
    count = run_rules(base)
    print(f"rules executed; <urn:gastrokg:inferred> holds {count} triples")

    reference = engine.reason_all_cases().graph
    different = 0
    for path in sorted((ROOT / "graphdb" / "queries").glob("cq*.rq")):
        query = path.read_text(encoding="utf-8")
        ours = sorted(tuple(normal(None if v is None else v.toPython()) for v in row) for row in reference.query(query))
        theirs = sorted(tuple(normal(v) for v in row) for row in select(base, query))
        same = ours == theirs
        different += not same
        print(f"  {'SAME     ' if same else 'DIFFERENT'} {path.stem} (python {len(ours)} rows, graphdb {len(theirs)})")
        if not same:
            print("      only python :", [r for r in ours if r not in theirs][:6])
            print("      only graphdb:", [r for r in theirs if r not in ours][:6])
    print("all competency questions agree" if not different else f"{different} competency question(s) differ")
    return 1 if different else 0


if __name__ == "__main__":
    sys.exit(main())
