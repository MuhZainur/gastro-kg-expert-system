"""Write graphdb/queries/*.rq: competency questions and visualization queries.

Run:  python scripts/make_queries.py
"""
from pathlib import Path

QUERIES = Path(__file__).resolve().parent.parent / "graphdb" / "queries"

PREFIXES = """PREFIX gk:      <http://example.org/gastrokg/ontology#>
PREFIX gkd:     <http://example.org/gastrokg/data#>
PREFIX rdfs:    <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos:    <http://www.w3.org/2004/02/skos/core#>
PREFIX dcterms: <http://purl.org/dc/terms/>
"""

ENGLISH = 'FILTER(LANG({0}) = "en" || LANG({0}) = "")'

# (file, question, body)
DEFINITIONS = [
    ("cq01-diseases-with-epigastric-pain", "Which diseases manifest as epigastric pain?", """
SELECT ?code ?disease WHERE {
  ?d gk:manifestsAs gkd:EpigastricPain ; gk:code ?code ; rdfs:label ?disease . """ + ENGLISH.format("?disease") + """
} ORDER BY ?code"""),
    ("cq02-emergency-symptoms", "Which symptoms are emergency symptoms? (sub-class inference, rdfs9 / rdfs11)", """
SELECT DISTINCT ?code ?symptom WHERE {
  ?s a gk:EmergencySymptom ; gk:code ?code ; rdfs:label ?symptom . """ + ENGLISH.format("?symptom") + """
} ORDER BY ?code"""),
    ("cq03-diseases-of-upper-gi-tract", "Which diseases affect the upper GI tract? (property chain + transitivity)", """
SELECT DISTINCT ?code ?disease WHERE {
  ?d gk:affects gkd:UpperGITract ; gk:code ?code ; rdfs:label ?disease . """ + ENGLISH.format("?disease") + """
} ORDER BY ?code"""),
    ("cq04-differential-diagnosis", "What is the ranked differential diagnosis of encounter E001?", """
SELECT ?rank ?code ?cf ?status ?coverage WHERE {
  ?h a gk:Hypothesis ; gk:ofEncounter gkd:E001 ; gk:rank ?rank ; gk:certaintyFactor ?cf ;
     gk:forDisease ?d ; gk:matchStatus ?s ; gk:ruleCoverage ?coverage .
  ?d gk:code ?code .
  BIND(STRAFTER(STR(?s), "#") AS ?status)
} ORDER BY ?rank"""),
    ("cq05-cf-trace", "How was the certainty factor of GERD in E001 built, step by step?", """
SELECT ?step ?symptom ?itemCF ?before ?after WHERE {
  ?item a gk:EvidenceItem ; gk:ofHypothesis gkd:E001_P03 ; gk:sequence ?step ; gk:itemCF ?itemCF ;
        gk:cumulativeBefore ?before ; gk:cumulativeAfter ?after ; gk:basedOnLink ?link .
  ?link gk:aboutSymptom ?s . ?s gk:code ?symptom .
} ORDER BY ?step"""),
    ("cq06-missing-conditions", "What is still missing to complete a rule in encounter E003?", """
SELECT ?disease ?coverage ?missing WHERE {
  ?h a gk:Hypothesis ; gk:ofEncounter gkd:E003 ; gk:forDisease ?d ; gk:ruleCoverage ?coverage ;
     gk:missingSymptom ?s .
  ?d gk:code ?disease . ?s gk:code ?missing .
} ORDER BY ?disease ?missing"""),
    ("cq07-emergency-cases", "Which encounters are emergencies, and because of which symptom?", """
SELECT ?encounter ?symptom WHERE {
  ?e a gk:Encounter ; gk:finalTriage gkd:Emergency .
  ?t a gk:TriageDecision ; gk:ofEncounter ?e ; gk:triageLevel gkd:Emergency ; gk:triggeredBy ?s .
  ?s gk:code ?symptom .
  BIND(STRAFTER(STR(?e), "#") AS ?encounter)
} ORDER BY ?encounter ?symptom"""),
    ("cq08-final-triage", "What is the final triage level and care facility of every encounter?", """
SELECT ?encounter ?level ?facility WHERE {
  ?e a gk:Encounter ; gk:finalTriage ?l .
  ?l gk:refersTo ?f .
  BIND(STRAFTER(STR(?e), "#") AS ?encounter)
  BIND(STRAFTER(STR(?l), "#") AS ?level)
  BIND(STRAFTER(STR(?f), "#") AS ?facility)
} ORDER BY ?encounter"""),
    ("cq09-nsaid-users", "Which patients does the reasoner classify as NSAID users? (property chain + hasValue)", """
SELECT DISTINCT ?patient WHERE {
  ?p a gk:NSAIDUser .
  BIND(STRAFTER(STR(?p), "#") AS ?patient)
} ORDER BY ?patient"""),
    ("cq10-safety-alerts", "Which medication safety alerts exist, how severe, and what could be discussed instead?", """
SELECT ?encounter ?medicine ?severity ?alternative ?reason WHERE {
  ?a a gk:SafetyAlert ; gk:ofEncounter ?e ; gk:concernsMedication ?m ; gk:severity ?severity ; gk:reason ?reason .
  OPTIONAL { ?a gk:suggestedAlternative ?alt }
  BIND(STRAFTER(STR(?e), "#") AS ?encounter)
  BIND(STRAFTER(STR(?m), "#") AS ?medicine)
  BIND(STRAFTER(STR(?alt), "#") AS ?alternative)
} ORDER BY ?encounter ?medicine ?reason"""),
    ("cq11-next-question", "What should the system ask next? (backward chaining)", """
SELECT ?encounter ?symptom ?score WHERE {
  ?q a gk:QuestionSuggestion ; gk:rank 1 ; gk:ofEncounter ?e ; gk:askSymptom ?s ; gk:discriminationScore ?score .
  ?s gk:code ?symptom .
  BIND(STRAFTER(STR(?e), "#") AS ?encounter)
} ORDER BY ?encounter"""),
    ("cq12-provenance", "Where do the certainty weights come from?", """
SELECT ?status ?sourceType (COUNT(DISTINCT ?link) AS ?links) WHERE {
  ?link a gk:EvidenceLink ; gk:weightStatus ?w ; dcterms:source ?src .
  BIND(STRAFTER(STR(?w), "#") AS ?status)
  BIND(IF(?src = gkd:GroupAssignment, "group assignment or modelling choice", "public health source") AS ?sourceType)
} GROUP BY ?status ?sourceType ORDER BY ?status ?sourceType"""),
    ("cq13-opposing-evidence", "Which evidence argues against a hypothesis in E011?", """
SELECT ?disease ?symptom ?itemCF WHERE {
  ?item a gk:EvidenceItem ; gk:ofEncounter gkd:E011 ; gk:polarity gkd:Oppose ; gk:itemCF ?itemCF ;
        gk:basedOnLink ?link .
  ?link gk:ofDisease ?d ; gk:aboutSymptom ?s .
  ?d gk:code ?disease . ?s gk:code ?symptom .
} ORDER BY ?disease ?symptom"""),
    ("cq14-ulcer-risk", "Which patients are at raised ulcer risk? (union of two defined classes)", """
SELECT DISTINCT ?patient WHERE {
  ?p a gk:UlcerRiskPatient .
  BIND(STRAFTER(STR(?p), "#") AS ?patient)
} ORDER BY ?patient"""),
    ("viz1-knowledge-network", "VISUAL GRAPH: diseases, their symptoms and anatomy", """
CONSTRUCT {
  ?d gk:manifestsAs ?s . ?d gk:affects ?site . ?site gk:partOf ?parent .
} WHERE {
  { ?d gk:manifestsAs ?s }
  UNION { ?d a gk:Disease ; gk:affects ?site . FILTER(?site = gkd:Stomach || ?site = gkd:Esophagus) }
  UNION { VALUES (?site ?parent) { (gkd:StomachLining gkd:Stomach) (gkd:Stomach gkd:UpperGITract)
                                   (gkd:Esophagus gkd:UpperGITract) (gkd:UpperGITract gkd:DigestiveSystem) } }
}"""),
    ("viz2-reasoning-trace-E001", "VISUAL GRAPH: CF chain of the GERD hypothesis in E001", """
CONSTRUCT {
  gkd:E001 gk:primaryHypothesis ?h .
  ?item gk:ofHypothesis ?h ; gk:previousStep ?prev ; gk:basedOnObservation ?obs ; gk:basedOnLink ?link .
  ?obs gk:observedSymptom ?s . ?link gk:aboutSymptom ?s .
  ?h gk:forDisease ?d .
} WHERE {
  gkd:E001 gk:primaryHypothesis ?h . ?h gk:forDisease ?d .
  ?item a gk:EvidenceItem ; gk:ofHypothesis ?h ; gk:basedOnObservation ?obs ; gk:basedOnLink ?link .
  ?obs gk:observedSymptom ?s .
  OPTIONAL { ?item gk:previousStep ?prev }
}"""),
    ("viz3-triage-and-safety-E007", "VISUAL GRAPH: patient, medicine, alerts and triage of E007", """
CONSTRUCT {
  ?p gk:hadEncounter gkd:E007 ; gk:takesMedication ?m . ?m gk:drugClass ?c .
  gkd:E007 gk:showsSymptom ?s ; gk:finalTriage ?level . ?level gk:refersTo ?place .
  ?alert gk:ofEncounter gkd:E007 ; gk:concernsMedication ?am ; gk:forDisease ?disease ;
         gk:suggestedAlternative ?alt .
} WHERE {
  ?p gk:hadEncounter gkd:E007 ; gk:takesMedication ?m . ?m gk:drugClass ?c .
  gkd:E007 gk:showsSymptom ?s ; gk:finalTriage ?level . ?level gk:refersTo ?place .
  ?alert a gk:SafetyAlert ; gk:ofEncounter gkd:E007 ; gk:concernsMedication ?am .
  OPTIONAL { ?alert gk:forDisease ?disease }
  OPTIONAL { ?alert gk:suggestedAlternative ?alt }
}"""),
    ("viz4-emergency-E004", "VISUAL GRAPH: why E004 is an emergency", """
CONSTRUCT {
  gkd:E004 gk:hasObservation ?obs ; gk:finalTriage ?level .
  ?obs gk:observedSymptom ?s .
  ?decision gk:ofEncounter gkd:E004 ; gk:triageLevel ?l ; gk:triggeredBy ?why .
  ?level gk:refersTo ?place .
} WHERE {
  gkd:E004 gk:hasObservation ?obs ; gk:finalTriage ?level . ?level gk:refersTo ?place .
  ?obs gk:observedSymptom ?s .
  ?decision a gk:TriageDecision ; gk:ofEncounter gkd:E004 ; gk:triageLevel ?l ; gk:triggeredBy ?why .
}"""),
]

if __name__ == "__main__":
    QUERIES.mkdir(parents=True, exist_ok=True)
    for old in QUERIES.glob("*.rq"):
        old.unlink()
    for name, question, body in DEFINITIONS:
        (QUERIES / f"{name}.rq").write_text(f"# {question}\n{PREFIXES}{body.strip()}\n", encoding="utf-8")
    print(f"written {len(DEFINITIONS)} queries to {QUERIES}")
