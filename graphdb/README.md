# GastroKG in GraphDB

Tested with GraphDB Free 11.5.2, ruleset **OWL2-RL (Optimized)**.

## Option A: one command

With GraphDB running on port 7200:

```
python scripts/graphdb_load.py
```

It creates the repository `gastrokg` (if missing), **replaces its content**, loads the three data
files, runs the 30 rules one commit at a time, and compares every competency question with the
Python engine. Other repositories are not touched.

## Option B: Workbench, by hand

1. **Setup > Repositories > Create from file**: `graphdb/repository-config.ttl`
   (or create a GraphDB repository with ruleset OWL2-RL (Optimized)).
2. **Import > Upload RDF files**, in this order, each into its named graph:

   | File | Named graph |
   |---|---|
   | `ontology/gastrokg-tbox.ttl` | `urn:gastrokg:tbox` |
   | `ontology/gastrokg-knowledge.ttl` | `urn:gastrokg:knowledge` |
   | `ontology/gastrokg-cases.ttl` | `urn:gastrokg:cases` |
   | `graphdb/gastrokg-inferred.ttl` | `urn:gastrokg:inferred` |

The last file holds the results of the SPARQL rules. RDFS and OWL conclusions are produced by
GraphDB itself. `shapes/gastrokg-shapes.ttl` is for validation and is not imported as data.

To show a rule running live, skip the last file and run the files in `graphdb/updates/` in
file-name order. Run each as its own query. Run `22-cf-next-step.ru` again and again until it adds
0 statements. Do not paste several rules into one request: later rules then miss earlier results.

## Visualisation

| What | Where |
|---|---|
| Class tree | **Explore > Class hierarchy** |
| Links between classes | **Explore > Class relationships** |
| Neighbourhood of one thing | **Explore > Visual graph**, search `E001`, `GERD`, `E007` |
| A prepared picture | **SPARQL**: run a `queries/viz*.rq` file, then press **Visual** |

| Query | Shows |
|---|---|
| `viz1-knowledge-network.rq` | Diseases, symptoms and anatomy |
| `viz2-reasoning-trace-E001.rq` | The certainty factor chain behind GERD |
| `viz3-triage-and-safety-E007.rq` | Patient, medicine, alerts and triage |
| `viz4-emergency-E004.rq` | Why a case is an emergency |

## Competency questions

`queries/cq01` to `cq14`. The question is the first line of each file. Keep **Include inferred
data** switched on.

## Contradiction demo

```sparql
PREFIX gk:  <http://example.org/gastrokg/ontology#>
PREFIX gkd: <http://example.org/gastrokg/data#>
INSERT DATA { gkd:GERD a gk:Symptom }
```

GraphDB rejects this with `Consistency check cax_dw_1 failed`, because `Symptom` and `Disease` are
disjoint.
