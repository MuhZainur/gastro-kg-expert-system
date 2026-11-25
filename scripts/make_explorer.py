"""Build docs/gastrokg-explorer.html: a self-contained, clickable map of the knowledge graph.

Everything shown is taken from the ontology files, the rules and a real reasoning run, so the
page cannot drift from the project. Run:  python scripts/make_explorer.py
"""
import json
import re
import sys
from pathlib import Path

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend.app import engine  # noqa: E402
from backend.app.engine import GK, GKD  # noqa: E402

NAMESPACES = [
    (str(GK), "gk:"), (str(GKD), "gkd:"), (str(RDF), "rdf:"), (str(RDFS), "rdfs:"), (str(OWL), "owl:"),
    ("http://www.w3.org/2004/02/skos/core#", "skos:"), ("http://purl.org/dc/terms/", "dcterms:"),
    ("http://www.w3.org/ns/prov#", "prov:"), ("http://www.w3.org/2001/XMLSchema#", "xsd:"),
    ("http://www.wikidata.org/entity/", "wd:"), ("http://purl.obolibrary.org/obo/", "obo:"),
]
SKIP_OBJECTS = {OWL.Thing, RDFS.Resource, OWL.Nothing}


def short(term):
    if isinstance(term, URIRef):
        for namespace, prefix in NAMESPACES:
            if str(term).startswith(namespace):
                return prefix + str(term)[len(namespace):]
    return str(term)


def term(text):
    """gk:Name / gkd:Name / rdfs:label -> URIRef."""
    if text == "a":
        return RDF.type
    prefix, local = text.split(":", 1)
    namespace = next(n for n, p in NAMESPACES if p == prefix + ":")
    return URIRef(namespace + local)


def local(node):
    return str(node).split("#")[-1]


# ------------------------------------------------------------------ reasoning, rule by rule
asserted = engine.load_graph(engine.TBOX, engine.KNOWLEDGE, engine.CASES)
rules = engine.load_rules()
graph = engine.reason(asserted, disabled=frozenset(r.name for r in rules)).graph
closure_size = len(graph)
produced = {}
for rule in rules:
    new, _, _ = engine.apply_rules(graph, [rule])
    produced[rule.name] = set(new)
rule_of = {triple: i for i, rule in enumerate(rules) for triple in produced[rule.name]}


def origin(triple):
    if triple in asserted:
        return "a"
    return rule_of.get(triple, "o")


def label(node, lang="en"):
    values = list(graph.objects(node, RDFS.label))
    for value in values:
        if getattr(value, "language", None) == lang:
            return str(value)
    return str(values[0]) if values else local(node)


def value(subject, predicate):
    found = graph.value(subject, predicate)
    return None if found is None else found.toPython() if isinstance(found, Literal) else found


def number(subject, predicate):
    found = value(subject, predicate)
    return None if found is None else float(found)


# ------------------------------------------------------------------ triples and node index
triples = []
for s, p, o in graph:
    if not isinstance(s, URIRef) or not str(s).startswith((str(GK), str(GKD))):
        continue
    if isinstance(o, BNode) or o in SKIP_OBJECTS or s == o or p == OWL.sameAs:
        continue
    source = origin((s, p, o))
    literal = isinstance(o, Literal)
    text = f"{o} @{o.language}" if literal and o.language else short(o)
    triples.append([short(s), short(p), text, int(literal), source])
triples.sort(key=lambda t: (t[0], t[1], t[2]))

CLASS_OF = {}
for s, _, o in graph.triples((None, RDF.type, None)):
    CLASS_OF.setdefault(s, set()).add(o)

DERIVED = {"Hypothesis", "EvidenceItem", "RuleMatch", "RuleFiring", "TriageDecision", "SafetyAlert",
           "Recommendation", "QuestionSuggestion", "InferredResult"}
FACT = {"Patient", "Encounter", "SymptomObservation"}


def describe(node):
    types = {local(t) for t in CLASS_OF.get(node, set()) if str(t).startswith(str(GK))}
    if (node, RDF.type, OWL.Class) in asserted:
        kind = "class"
    elif str(node).startswith(str(GK)):
        kind = "property"
    elif types & DERIVED:
        kind = "derived"
    elif types & FACT:
        kind = "fact"
    else:
        kind = "knowledge"
    name = local(node)
    if "Hypothesis" in types:
        cf = number(node, GK.certaintyFactor)
        name = f"{local(value(node, GK.forDisease))} {cf:.3f}"
    elif "SymptomObservation" in types:
        code = name.split("_")[-1]
        name = f"obs {code} ({number(node, GK.userCF)})"
    elif "SafetyAlert" in types:
        name = "Alert " + " + ".join(sorted(local(m) for m in graph.objects(node, GK.concernsMedication)))
        disease = value(node, GK.forDisease)
        if disease:
            name += f": {local(disease)}"
    elif any(t.endswith("Symptom") for t in types):
        name = f"{value(node, GK.code)} {name}"
    return {"kind": kind, "name": name, "label": label(node), "labelId": label(node, "id")}


nodes = {}
for s, p, o, literal, _ in triples:
    for text in (s, None if literal else o):
        if text and text.startswith(("gk:", "gkd:")) and text not in nodes:
            nodes[text] = describe(term(text))

# ------------------------------------------------------------------ cases
cases = []
for encounter in sorted(asserted.subjects(RDF.type, GK.Encounter)):
    patient = next(asserted.subjects(GK.hadEncounter, encounter))
    observations = []
    for obs in asserted.objects(encounter, GK.hasObservation):
        symptom = asserted.value(obs, GK.observedSymptom) or asserted.value(obs, GK.deniedSymptom)
        observations.append({
            "code": str(value(symptom, GK.code)), "id": short(symptom), "label": label(symptom),
            "labelId": label(symptom, "id"), "cf": number(obs, GK.userCF),
            "denied": (obs, GK.deniedSymptom, symptom) in asserted})
    observations.sort(key=lambda o: o["code"])

    owl_facts = []
    watched = {"EmergencyEncounter", "AlarmEncounter", "DyspepticEncounter", "NSAIDUser", "AnticoagulantUser",
               "HPyloriHistoryPatient", "UlcerRiskPatient"}
    for node in (encounter, patient):
        for p, o in graph.predicate_objects(node):
            if origin((node, p, o)) != "o":
                continue
            if (p == RDF.type and local(o) in watched) or p in (GK.showsSymptom, GK.takesDrugClass, GK.encounterOf):
                owl_facts.append([short(node), "a" if p == RDF.type else short(p), short(o)])

    hypotheses = []
    for h in graph.subjects(GK.ofEncounter, encounter):
        if (h, RDF.type, GK.Hypothesis) not in graph:
            continue
        disease = value(h, GK.forDisease)
        steps = []
        for item in graph.subjects(GK.ofHypothesis, h):
            link = value(item, GK.basedOnLink)
            obs = value(item, GK.basedOnObservation)
            symptom = value(link, GK.aboutSymptom)
            denied = (obs, GK.deniedSymptom, symptom) in graph
            steps.append({
                "seq": int(value(item, GK.sequence)), "oppose": value(item, GK.polarity) == GKD.Oppose,
                "code": str(value(symptom, GK.code)), "label": label(symptom), "denied": denied,
                "user": number(obs, GK.userCF),
                "expert": number(link, GK.absenceCF if denied else GK.expertCF),
                "cf": number(item, GK.itemCF), "before": number(item, GK.cumulativeBefore),
                "after": number(item, GK.cumulativeAfter),
                "source": sorted(short(s) for s in graph.objects(link, term("dcterms:source")))})
        steps.sort(key=lambda s: (s["oppose"], s["seq"]))
        hypotheses.append({
            "id": short(h), "disease": local(disease), "label": label(disease),
            "cf": number(h, GK.certaintyFactor), "support": number(h, GK.supportCF),
            "oppose": number(h, GK.oppositionCF), "coverage": number(h, GK.ruleCoverage),
            "status": local(value(h, GK.matchStatus)), "rank": int(value(h, GK.rank)), "steps": steps,
            "missing": sorted(str(value(s, GK.code)) + " " + label(s) for s in graph.objects(h, GK.missingSymptom)),
            "risks": sorted(label(r) for r in graph.objects(h, GK.contextRiskFactor))})
    hypotheses.sort(key=lambda h: h["rank"])

    reported = {o["id"] for o in observations if not o["denied"]}
    matches = []
    for m in graph.subjects(GK.ofEncounter, encounter):
        if (m, RDF.type, GK.RuleMatch) not in graph:
            continue
        rule = value(m, GK.evaluatesRule) if (m, GK.firedRule, None) not in graph else value(m, GK.firedRule)
        matches.append({
            "rule": local(rule), "disease": local(value(m, GK.forDisease)),
            "matched": int(value(m, GK.matchedCount)), "required": int(value(m, GK.requiredCount)),
            "fired": (m, RDF.type, GK.RuleFiring) in graph,
            "conditions": sorted(({"code": str(value(s, GK.code)), "label": label(s), "met": short(s) in reported}
                                  for s in asserted.objects(rule, GK.requiresSymptom)), key=lambda c: c["code"])})
    matches.sort(key=lambda m: (not m["fired"], -m["matched"] / m["required"], m["rule"]))

    def of_type(cls):
        return sorted(s for s in graph.subjects(GK.ofEncounter, encounter) if (s, RDF.type, cls) in graph)

    alerts = [{
        "medicines": sorted(local(m) for m in graph.objects(a, GK.concernsMedication)),
        "disease": local(value(a, GK.forDisease)) if value(a, GK.forDisease) else None,
        "severity": str(value(a, GK.severity)), "reason": str(value(a, GK.reason)),
        "alternative": [local(x) for x in graph.objects(a, GK.suggestedAlternative)],
    } for a in of_type(GK.SafetyAlert)]
    decisions = [{
        "level": local(value(d, GK.triageLevel)), "reason": str(value(d, GK.reason)),
        "priority": int(value(value(d, GK.triageLevel), GK.priority)),
        "by": sorted(label(x) for x in graph.objects(d, GK.triggeredBy)),
    } for d in of_type(GK.TriageDecision)]
    decisions.sort(key=lambda d: -d["priority"])
    final = value(encounter, GK.finalTriage)
    recommendations = [{
        "text": str(value(r, GK.adviceText)),
        "exams": sorted(label(x) for x in graph.objects(r, GK.recommendsExamination)),
    } for r in of_type(GK.Recommendation)]
    question = None
    for q in of_type(GK.QuestionSuggestion):
        if (q, GK.rank, None) in graph:
            symptom = value(q, GK.askSymptom)
            question = {"code": str(value(symptom, GK.code)), "label": label(symptom),
                        "labelId": label(symptom, "id"), "score": number(q, GK.discriminationScore)}

    cases.append({
        "id": local(encounter), "title": label(encounter).split(": ", 1)[-1], "patient": short(patient),
        "age": int(value(patient, GK.age)),
        "risks": sorted(label(r) for r in asserted.objects(patient, GK.hasRiskFactor)),
        "medicines": sorted(local(m) for m in asserted.objects(patient, GK.takesRegularly)),
        "observations": observations, "owl": sorted(owl_facts), "hypotheses": hypotheses, "matches": matches,
        "alerts": alerts, "decisions": decisions,
        "final": {"level": local(final), "label": label(final), "labelId": label(final, "id"),
                  "place": label(value(final, GK.refersTo))},
        "recommendations": recommendations, "question": question})


# ------------------------------------------------------------------ source snippets
def snippet(path, subject):
    """Lines of one Turtle statement block, copied from the file."""
    lines = path.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if line.startswith(subject + " ") or line.startswith(subject + "\t"):
            block = []
            for following in lines[i:]:
                block.append(following)
                if re.search(r"\.\s*(#.*)?$", following):
                    return "\n".join(block)
    raise ValueError(f"{subject} not found in {path.name}")


# ------------------------------------------------------------------ inference examples (verified)
def proof(key, layer, rule, title, explain, premises, conclusion, snippets=()):
    for text in premises:
        assert tuple(term(x) for x in text.split()) in graph, f"{key}: premise missing: {text}"
    for text in conclusion:
        triple = tuple(term(x) for x in text.split())
        assert triple in graph, f"{key}: conclusion missing: {text}"
        assert triple not in asserted, f"{key}: conclusion is asserted, not inferred: {text}"
    code = "\n\n".join(snippet(engine.TBOX, s) for s in snippets)
    return {"key": key, "layer": layer, "rule": rule, "title": title, "explain": explain,
            "premises": premises, "conclusion": conclusion, "code": code}


proofs = [
    proof("subclass", "rdfs", "rdfs9 / cax-sco", "Pewarisan kelas",
          "Muntah darah ditulis hanya sebagai gejala perdarahan. Karena gejala perdarahan adalah sub-kelas gejala gawat darurat, reasoner menambahkan tipe itu sendiri.",
          ["gkd:VomitingBlood a gk:BleedingSymptom", "gk:BleedingSymptom rdfs:subClassOf gk:EmergencySymptom"],
          ["gkd:VomitingBlood a gk:EmergencySymptom"], ["gk:BleedingSymptom"]),
    proof("transitive-class", "rdfs", "rdfs11 / scm-sco", "Rantai sub-kelas",
          "Dua tingkat hierarki digabung menjadi satu hubungan langsung.",
          ["gk:BleedingSymptom rdfs:subClassOf gk:EmergencySymptom",
           "gk:EmergencySymptom rdfs:subClassOf gk:AlarmSymptom"],
          ["gk:BleedingSymptom rdfs:subClassOf gk:AlarmSymptom"], ["gk:EmergencySymptom"]),
    proof("subproperty", "rdfs", "rdfs7 / prp-spo1", "Pewarisan properti",
          "Minum obat secara rutin berarti juga minum obat.",
          ["gk:takesRegularly rdfs:subPropertyOf gk:takesMedication", "gkd:PT007 gk:takesRegularly gkd:Ibuprofen"],
          ["gkd:PT007 gk:takesMedication gkd:Ibuprofen"], ["gk:takesRegularly"]),
    proof("inverse", "owl", "prp-inv", "Properti kebalikan",
          "Cukup menulis pasien punya kunjungan. Arah sebaliknya disimpulkan.",
          ["gk:encounterOf owl:inverseOf gk:hadEncounter", "gkd:PT001 gk:hadEncounter gkd:E001"],
          ["gkd:E001 gk:encounterOf gkd:PT001"], ["gk:encounterOf"]),
    proof("chain", "owl", "prp-spo2", "Rantai properti",
          "Minum obat, lalu obat termasuk golongan tertentu, berarti pasien memakai golongan obat itu.",
          ["gkd:PT007 gk:takesMedication gkd:Ibuprofen", "gkd:Ibuprofen gk:drugClass gkd:NSAID"],
          ["gkd:PT007 gk:takesDrugClass gkd:NSAID"], ["gk:takesDrugClass"]),
    proof("hasvalue", "owl", "cls-hv2 + cls-int1", "Definisi kelas: pengguna NSAID",
          "NSAIDUser didefinisikan sebagai pasien yang golongan obatnya NSAID. Tidak ada pasien yang ditulis sebagai NSAIDUser.",
          ["gkd:PT007 a gk:Patient", "gkd:PT007 gk:takesDrugClass gkd:NSAID"],
          ["gkd:PT007 a gk:NSAIDUser"], ["gk:NSAIDUser"]),
    proof("union", "owl", "cls-uni + cax-sco", "Gabungan dua kelas",
          "Pengguna NSAID atau pasien dengan riwayat H. pylori termasuk pasien berisiko tukak.",
          ["gkd:PT007 a gk:NSAIDUser"], ["gkd:PT007 a gk:UlcerRiskPatient"], ["gk:UlcerRiskPatient"]),
    proof("somevalues", "owl", "cls-svf1 + cls-int1", "Klasifikasi gawat darurat",
          "Kunjungan yang menunjukkan minimal satu gejala gawat darurat diklasifikasikan otomatis. Premisnya sendiri hasil inferensi sebelumnya.",
          ["gkd:E004 a gk:Encounter", "gkd:E004 gk:showsSymptom gkd:VomitingBlood",
           "gkd:VomitingBlood a gk:EmergencySymptom"],
          ["gkd:E004 a gk:EmergencyEncounter"], ["gk:EmergencyEncounter"]),
    proof("transitive", "owl", "prp-trp", "Properti transitif",
          "Gawat darurat lebih mendesak daripada segera, segera lebih mendesak daripada rujukan. Rule triase memakai kesimpulan ini.",
          ["gkd:Emergency gk:moreUrgentThan gkd:Urgent", "gkd:Urgent gk:moreUrgentThan gkd:Referral"],
          ["gkd:Emergency gk:moreUrgentThan gkd:Referral"], ["gk:moreUrgentThan"]),
    proof("anatomy", "owl", "prp-spo2", "Lokasi anatomi",
          "Penyakit yang mengenai lapisan lambung juga mengenai lambung.",
          ["gkd:Gastritis gk:affects gkd:StomachLining", "gkd:StomachLining gk:partOf gkd:Stomach"],
          ["gkd:Gastritis gk:affects gkd:Stomach"], ["gk:affects"]),
]

# Every node in our files is already typed, so domain is shown with a throwaway triple, really reasoned.
trial = engine.load_graph(engine.TBOX)
trial.add((GKD.ContohBaru, GK.manifestsAs, GKD.Nausea))
assert (GKD.ContohBaru, RDF.type, GK.Disease) not in trial
trial = engine.reason(trial, disabled=frozenset(r.name for r in rules)).graph
assert (GKD.ContohBaru, RDF.type, GK.Disease) in trial
proofs.insert(3, {
    "key": "domain", "layer": "rdfs", "rule": "rdfs2 / prp-dom", "title": "Domain menambahkan tipe",
    "explain": "Uji coba, tidak ada di file data: node baru tanpa tipe diberi satu triple. Domain bukan pemeriksaan, "
               "jadi reasoner tidak menolak melainkan menyimpulkan bahwa node itu penyakit.",
    "premises": ["gkd:ContohBaru gk:manifestsAs gkd:Nausea"], "conclusion": ["gkd:ContohBaru a gk:Disease"],
    "code": snippet(engine.TBOX, "gk:manifestsAs")})

step = next(s for c in cases if c["id"] == "E001" for h in c["hypotheses"] if h["disease"] == "GERD"
            for s in h["steps"] if s["code"] == "G02")
proofs.append({
    "key": "cf", "layer": "sparql", "rule": "22-cf-next-step", "title": "Menghitung certainty factor",
    "explain": "RDFS dan OWL tidak bisa menghitung. Rule SPARQL menggabungkan bukti satu per satu dan menyimpan tiap langkah sebagai node.",
    "premises": [f"CF sebelumnya = {step['before']}", f"CF gejala G02 = {step['user']} x {step['expert']} = {step['cf']:g}"],
    "conclusion": [f"CF baru = {step['before']} + {step['cf']:g} x (1 - {step['before']}) = {step['after']:g}"],
    "code": next(r.query for r in rules if r.name == "22-cf-next-step")})
proofs.append({
    "key": "negation", "layer": "sparql", "rule": "75-triage-self-monitor", "title": "Negasi: tidak ada keputusan lain",
    "explain": "OWL memakai asumsi dunia terbuka, jadi tidak bisa menyimpulkan dari ketiadaan fakta. SPARQL bisa, dengan FILTER NOT EXISTS.",
    "premises": ["E010 tidak punya TriageDecision dari rule 70-74"],
    "conclusion": ["E010 mendapat keputusan SelfMonitor"],
    "code": next(r.query for r in rules if r.name == "75-triage-self-monitor")})
proofs.append({
    "key": "disjoint", "layer": "owl", "rule": "cax-dw", "title": "Mendeteksi kontradiksi",
    "explain": "Symptom dan Disease dinyatakan saling lepas. Menyatakan GERD sebagai gejala ditolak. Pesan di bawah berasal dari uji di GraphDB 11.5.2.",
    "premises": ["gk:Symptom dan gk:Disease: owl:AllDisjointClasses", "INSERT: gkd:GERD a gk:Symptom"],
    "conclusion": ["DITOLAK: Consistency check cax_dw_1 failed"],
    "code": "INSERT DATA { gkd:GERD a gk:Symptom }"})

bad = engine.load_graph(engine.KNOWLEDGE, engine.CASES)
bad.remove((GKD.EL_P01_G01, GK.expertCF, None))
bad.parse(format="turtle", data=f"<{GKD.EL_P01_G01}> <{GK.expertCF}> 1.5 .")
conforms, report = engine.shacl_report(bad)
assert not conforms
proofs.append({
    "key": "shacl", "layer": "shacl", "rule": "gk:EvidenceLinkShape", "title": "Menolak data yang salah",
    "explain": "Bobot pakar 1.5 sengaja dimasukkan. SHACL melaporkannya sebelum penalaran berjalan. Di bawah ini laporan aslinya.",
    "premises": ["gkd:EL_P01_G01 gk:expertCF 1.5"],
    "conclusion": ["Conforms: False. Expert CF must lie strictly between -1 and 1."],
    "code": report.strip()})

# ------------------------------------------------------------------ rules
GROUPS = [("Pengayaan pengetahuan", ["01"]), ("Forward chaining", ["10", "40", "41"]),
          ("Certainty factor", ["20", "21", "22", "30"]), ("Status dan ranking", ["42", "43", "44", "45", "50", "51"]),
          ("Konteks dan keamanan obat", ["60", "61", "62"]), ("Triase", ["70", "71", "72", "73", "74", "75", "76"]),
          ("Rekomendasi", ["90", "91", "92"]), ("Backward chaining", ["46", "95", "96"])]
rule_data = []
for i, rule in enumerate(rules):
    group = next(g for g, numbers in GROUPS if rule.name[:2] in numbers)
    sample = sorted(([short(s), short(p), short(o)] for s, p, o in produced[rule.name]))[:8]
    rule_data.append({"name": rule.name, "title": rule.title, "description": rule.description,
                      "iterate": rule.iterate, "query": rule.query, "count": len(produced[rule.name]),
                      "group": group, "sample": sample})

data = {
    "stats": {"asserted": len(asserted), "closure": closure_size,
              "rules": sum(len(v) for v in produced.values()), "ruleCount": len(rules), "cases": len(cases)},
    "files": [{"name": p.relative_to(ROOT).as_posix(), "triples": len(Graph().parse(p, format="turtle")),
               "role": role} for p, role in [
        (engine.TBOX, "T-Box: kelas, properti, definisi OWL"),
        (engine.KNOWLEDGE, "A-Box pengetahuan: penyakit, gejala, bobot, rule, obat"),
        (engine.CASES, "A-Box kasus: pasien sintetis")]],
    "shapes": engine.SHAPES.read_text(encoding="utf-8"),
    "triples": triples, "nodes": nodes, "cases": cases, "rules": rule_data, "proofs": proofs,
}

template = (ROOT / "docs" / "explorer.template.html").read_text(encoding="utf-8")
payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
assert "/*__DATA__*/null" in template
out = ROOT / "docs" / "gastrokg-explorer.html"
out.write_text(template.replace("/*__DATA__*/null", payload), encoding="utf-8")
print(f"{out.relative_to(ROOT)}: {out.stat().st_size / 1024:.0f} KB, {len(triples)} triples, "
      f"{len(nodes)} nodes, {len(proofs)} verified examples")
