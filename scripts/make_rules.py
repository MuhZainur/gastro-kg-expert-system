"""Write rules/*.rq from the definitions below, each as a standalone SPARQL CONSTRUCT.

Run:  python scripts/make_rules.py
"""
from pathlib import Path

RULES = Path(__file__).resolve().parent.parent / "rules"

PREFIXES = """PREFIX gk:   <http://example.org/gastrokg/ontology#>
PREFIX gkd:  <http://example.org/gastrokg/data#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""

# (file name, title, description, repeat until nothing new, query body)
DEFINITIONS = [
    ("01-manifestation", "Disease manifests as symptom",
     "Direct disease-symptom edges from supporting evidence links.", False, """
CONSTRUCT { ?disease gk:manifestsAs ?symptom }
WHERE {
  ?link a gk:EvidenceLink ; gk:ofDisease ?disease ; gk:aboutSymptom ?symptom ; gk:expertCF ?w .
  FILTER(?w > 0)
}"""),
    ("10-evidence-item", "Forward chaining: match facts to evidence",
     "Each reported or denied symptom activates the evidence links that mention it. CF = patient certainty x expert CF.",
     False, """
CONSTRUCT {
  ?hypothesis a gk:Hypothesis ; gk:ofEncounter ?encounter ; gk:forDisease ?disease .
  ?item a gk:EvidenceItem ; rdfs:label ?label ; gk:ofEncounter ?encounter ; gk:ofHypothesis ?hypothesis ;
        gk:basedOnObservation ?obs ; gk:basedOnLink ?link ; gk:itemCF ?cf ; gk:polarity ?polarity .
}
WHERE {
  ?encounter a gk:Encounter ; gk:hasObservation ?obs .
  ?obs gk:userCF ?user .
  {
    ?obs gk:observedSymptom ?symptom .
    ?link a gk:EvidenceLink ; gk:aboutSymptom ?symptom ; gk:ofDisease ?disease ; gk:expertCF ?weight .
    BIND("reports" AS ?verb)
  } UNION {
    ?obs gk:deniedSymptom ?symptom .
    ?link a gk:EvidenceLink ; gk:aboutSymptom ?symptom ; gk:ofDisease ?disease ; gk:absenceCF ?weight .
    BIND("denies" AS ?verb)
  }
  BIND(?user * ?weight AS ?cf)
  FILTER(?cf != 0)
  BIND(IF(?cf > 0, gkd:Support, gkd:Oppose) AS ?polarity)
  ?symptom gk:code ?sc .
  ?disease gk:code ?dc .
  BIND(IRI(CONCAT(STR(?encounter), "_", ?dc)) AS ?hypothesis)
  BIND(IRI(CONCAT(STR(?encounter), "_", ?dc, "_", ?sc)) AS ?item)
  BIND(CONCAT(STRAFTER(STR(?encounter), "#"), " ", ?verb, " ", ?sc, " -> ", ?dc, " (CF ", STR(?cf), ")") AS ?label)
}"""),
    ("20-sequence", "Order the evidence",
     "Number the evidence of each hypothesis by symptom code, separately for supporting and opposing items.",
     False, """
CONSTRUCT { ?item gk:sequence ?n }
WHERE {
  {
    SELECT ?item (COUNT(?other) AS ?before)
    WHERE {
      ?item a gk:EvidenceItem ; gk:ofHypothesis ?h ; gk:polarity ?p ; gk:basedOnLink ?link .
      ?link gk:aboutSymptom ?s . ?s gk:code ?code .
      OPTIONAL {
        ?other a gk:EvidenceItem ; gk:ofHypothesis ?h ; gk:polarity ?p ; gk:basedOnLink ?otherLink .
        ?otherLink gk:aboutSymptom ?otherSymptom . ?otherSymptom gk:code ?otherCode .
        FILTER(?otherCode < ?code)
      }
    }
    GROUP BY ?item
  }
  BIND(?before + 1 AS ?n)
}"""),
    ("21-cf-first-step", "Certainty factor: first step",
     "The first evidence of a chain sets the combined CF.", False, """
CONSTRUCT { ?item gk:cumulativeBefore 0.0 ; gk:cumulativeAfter ?cf }
WHERE { ?item a gk:EvidenceItem ; gk:sequence 1 ; gk:itemCF ?cf }"""),
    ("22-cf-next-step", "Certainty factor: sequential combination",
     "Support: old + new x (1 - old). Opposition: old + new x (1 + old). Repeats along the chain.", True, """
CONSTRUCT { ?item gk:previousStep ?prevItem ; gk:cumulativeBefore ?old ; gk:cumulativeAfter ?new }
WHERE {
  ?prevItem a gk:EvidenceItem ; gk:ofHypothesis ?h ; gk:polarity ?p ; gk:sequence ?k ; gk:cumulativeAfter ?old .
  ?item a gk:EvidenceItem ; gk:ofHypothesis ?h ; gk:polarity ?p ; gk:sequence ?n ; gk:itemCF ?cf .
  FILTER(?n = ?k + 1)
  BIND(IF(?p = gkd:Support, ?old + ?cf * (1 - ?old), ?old + ?cf * (1 + ?old)) AS ?new)
}"""),
    ("30-hypothesis-cf", "Certainty factor of each hypothesis",
     "Join the last supporting and opposing steps with the MYCIN formula (P + N) / (1 - min(|P|, |N|)).",
     False, """
CONSTRUCT {
  ?h rdfs:label ?label ; gk:supportCF ?p ; gk:oppositionCF ?n ; gk:certaintyFactor ?cf .
}
WHERE {
  ?h a gk:Hypothesis ; gk:ofEncounter ?encounter ; gk:forDisease ?disease .
  ?disease rdfs:label ?name . FILTER(LANG(?name) = "en")
  OPTIONAL {
    ?lastSupport a gk:EvidenceItem ; gk:ofHypothesis ?h ; gk:polarity gkd:Support ; gk:cumulativeAfter ?pa .
    FILTER NOT EXISTS { ?later gk:previousStep ?lastSupport }
  }
  OPTIONAL {
    ?lastOppose a gk:EvidenceItem ; gk:ofHypothesis ?h ; gk:polarity gkd:Oppose ; gk:cumulativeAfter ?na .
    FILTER NOT EXISTS { ?later2 gk:previousStep ?lastOppose }
  }
  BIND(COALESCE(?pa, 0.0) AS ?p)
  BIND(COALESCE(?na, 0.0) AS ?n)
  BIND(IF(ABS(?p) < ABS(?n), ABS(?p), ABS(?n)) AS ?smaller)
  BIND((?p + ?n) / (1 - ?smaller) AS ?cf)
  BIND(CONCAT(STRAFTER(STR(?encounter), "#"), " ", ?name, ": CF ",
              STR(ROUND(?cf * 10000) / 10000)) AS ?label)
}"""),
    ("40-rule-match", "Forward chaining: evaluate IF-THEN rules",
     "Count how many conditions of each diagnostic rule the encounter satisfies.", False, """
CONSTRUCT {
  ?match a gk:RuleMatch ; rdfs:label ?label ; gk:ofEncounter ?encounter ; gk:evaluatesRule ?rule ;
         gk:forDisease ?disease ; gk:matchedCount ?matched ; gk:requiredCount ?required ;
         gk:ruleCoverage ?coverage .
}
WHERE {
  {
    SELECT ?encounter ?rule (COUNT(DISTINCT ?need) AS ?required) (COUNT(DISTINCT ?hit) AS ?matched)
    WHERE {
      ?rule a gk:DiagnosticRule ; gk:requiresSymptom ?need .
      ?encounter a gk:Encounter .
      OPTIONAL { ?encounter gk:showsSymptom ?need . BIND(?need AS ?hit) }
    }
    GROUP BY ?encounter ?rule
  }
  FILTER(?matched > 0)
  ?rule gk:concludes ?disease ; gk:code ?rc .
  BIND(?matched / ?required AS ?coverage)
  BIND(IRI(CONCAT(STR(?encounter), "_", ?rc)) AS ?match)
  BIND(CONCAT(STRAFTER(STR(?encounter), "#"), " ", ?rc, ": ", STR(?matched), "/", STR(?required),
              " conditions") AS ?label)
}"""),
    ("41-rule-firing", "Forward chaining: fire rules",
     "A rule fires when every condition is satisfied (the strict AND of the original system).", False, """
CONSTRUCT { ?match a gk:RuleFiring ; gk:firedRule ?rule }
WHERE {
  ?match a gk:RuleMatch ; gk:evaluatesRule ?rule ; gk:matchedCount ?m ; gk:requiredCount ?r .
  FILTER(?m = ?r)
}"""),
    ("42-coverage", "Best rule coverage per hypothesis",
     "The highest share of conditions satisfied by any rule of that disease.", False, """
CONSTRUCT { ?h gk:ruleCoverage ?coverage }
WHERE {
  ?h a gk:Hypothesis ; gk:ofEncounter ?encounter ; gk:forDisease ?disease .
  OPTIONAL {
    SELECT ?encounter ?disease (MAX(?c) AS ?best)
    WHERE { ?m a gk:RuleMatch ; gk:ofEncounter ?encounter ; gk:forDisease ?disease ; gk:ruleCoverage ?c }
    GROUP BY ?encounter ?disease
  }
  BIND(COALESCE(?best, 0.0) AS ?coverage)
}"""),
    ("43-status-full", "Match status: full rule",
     "At least one rule of the disease fired.", False, """
CONSTRUCT { ?h gk:matchStatus gkd:FullRuleMatch }
WHERE {
  ?h a gk:Hypothesis ; gk:ofEncounter ?encounter ; gk:forDisease ?disease .
  ?f a gk:RuleFiring ; gk:ofEncounter ?encounter ; gk:forDisease ?disease .
}"""),
    ("44-status-partial", "Match status: partial",
     "No rule fired, but enough conditions of one rule are met (thresholds come from the policy node).", False, """
CONSTRUCT { ?h gk:matchStatus gkd:PartialMatch }
WHERE {
  gkd:Policy gk:partialMinSymptoms ?minSymptoms ; gk:partialMinCoverage ?minCoverage .
  ?h a gk:Hypothesis ; gk:ofEncounter ?encounter ; gk:forDisease ?disease .
  ?m a gk:RuleMatch ; gk:ofEncounter ?encounter ; gk:forDisease ?disease ;
     gk:matchedCount ?k ; gk:ruleCoverage ?c .
  FILTER(?k >= ?minSymptoms && ?c >= ?minCoverage)
  FILTER NOT EXISTS { ?h gk:matchStatus gkd:FullRuleMatch }
}"""),
    ("45-status-weak", "Match status: weak",
     "Everything else keeps its CF but is flagged as weak.", False, """
CONSTRUCT { ?h gk:matchStatus gkd:WeakMatch }
WHERE {
  ?h a gk:Hypothesis .
  FILTER NOT EXISTS { ?h gk:matchStatus ?any }
}"""),
    ("46-missing-symptom", "Backward chaining: what would complete the rule",
     "For a partially matched hypothesis, list the conditions of its best rule that were not asked yet.",
     False, """
CONSTRUCT { ?h gk:missingSymptom ?symptom }
WHERE {
  ?h a gk:Hypothesis ; gk:matchStatus gkd:PartialMatch ; gk:ofEncounter ?encounter ;
     gk:forDisease ?disease ; gk:ruleCoverage ?coverage .
  ?m a gk:RuleMatch ; gk:ofEncounter ?encounter ; gk:forDisease ?disease ;
     gk:ruleCoverage ?coverage ; gk:evaluatesRule ?rule .
  ?rule gk:requiresSymptom ?symptom .
  FILTER NOT EXISTS { ?encounter gk:hasObservation ?o . ?o gk:observedSymptom ?symptom }
  FILTER NOT EXISTS { ?encounter gk:hasObservation ?d . ?d gk:deniedSymptom ?symptom }
}"""),
    ("50-ranking", "Rank the differential diagnosis",
     "Order by match status, then certainty factor, then disease code.", False, """
CONSTRUCT { ?h gk:rank ?rank }
WHERE {
  {
    SELECT ?h (COUNT(?other) AS ?better)
    WHERE {
      ?h a gk:Hypothesis ; gk:ofEncounter ?encounter ; gk:certaintyFactor ?cf ;
         gk:matchStatus ?status ; gk:forDisease ?disease .
      ?status gk:priority ?priority . ?disease gk:code ?code .
      OPTIONAL {
        ?other a gk:Hypothesis ; gk:ofEncounter ?encounter ; gk:certaintyFactor ?cf2 ;
               gk:matchStatus ?status2 ; gk:forDisease ?disease2 .
        ?status2 gk:priority ?priority2 . ?disease2 gk:code ?code2 .
        FILTER(?priority2 > ?priority ||
               (?priority2 = ?priority && (?cf2 > ?cf || (?cf2 = ?cf && ?code2 < ?code))))
      }
    }
    GROUP BY ?h
  }
  BIND(?better + 1 AS ?rank)
}"""),
    ("51-primary-hypothesis", "Primary hypothesis",
     "The first ranked hypothesis counts only if it is better than weak.", False, """
CONSTRUCT { ?encounter gk:primaryHypothesis ?h }
WHERE {
  ?h a gk:Hypothesis ; gk:ofEncounter ?encounter ; gk:rank 1 ; gk:certaintyFactor ?cf ; gk:matchStatus ?status .
  FILTER(?status != gkd:WeakMatch && ?cf > 0)
}"""),
    ("60-context-risk", "Explain with patient risk factors",
     "Attach the patient's risk factors that are linked to the disease. They do not change the CF.", False, """
CONSTRUCT { ?h gk:contextRiskFactor ?risk }
WHERE {
  ?h a gk:Hypothesis ; gk:ofEncounter ?encounter ; gk:forDisease ?disease .
  ?encounter gk:encounterOf ?patient .
  ?patient gk:hasRiskFactor ?risk .
  ?risk gk:increasesRiskOf ?disease .
}"""),
    ("61-safety-drug-disease", "Safety: medicine and suspected disease",
     "A medicine the patient takes has a caution for a supported hypothesis.", False, """
CONSTRUCT {
  ?alert a gk:SafetyAlert ; rdfs:label ?label ; gk:ofEncounter ?encounter ; gk:concernsMedication ?medicine ;
         gk:forDisease ?disease ; gk:severity ?severity ; gk:reason ?why ; gk:triggeredBy ?caution , ?h ;
         gk:suggestedAlternative ?alternative .
}
WHERE {
  gkd:Policy gk:alertMinCF ?minimum .
  ?encounter gk:encounterOf ?patient .
  ?patient gk:takesMedication ?medicine .
  ?medicine gk:drugClass ?class .
  ?caution a gk:DrugCaution ; gk:cautionDrugClass ?class ; gk:cautionDisease ?disease ;
           gk:severity ?severity ; gk:reason ?why .
  ?h a gk:Hypothesis ; gk:ofEncounter ?encounter ; gk:forDisease ?disease ;
     gk:certaintyFactor ?cf ; gk:matchStatus ?status .
  FILTER(?status != gkd:WeakMatch && ?cf >= ?minimum)
  OPTIONAL { ?class gk:saferAlternative ?alternative }
  ?disease gk:code ?dc .
  BIND(STRAFTER(STR(?medicine), "#") AS ?mn)
  BIND(IRI(CONCAT(STR(?encounter), "_A_", ?mn, "_", ?dc)) AS ?alert)
  BIND(CONCAT(STRAFTER(STR(?encounter), "#"), " alert: ", ?mn, " with suspected ", STRAFTER(STR(?disease), "#")) AS ?label)
}"""),
    ("62-safety-interaction", "Safety: drug-drug interaction",
     "Two medicines of the patient belong to interacting classes.", False, """
CONSTRUCT {
  ?alert a gk:SafetyAlert ; rdfs:label ?label ; gk:ofEncounter ?encounter ;
         gk:concernsMedication ?first , ?second ; gk:severity ?severity ; gk:reason ?why ;
         gk:triggeredBy ?interaction .
}
WHERE {
  ?encounter gk:encounterOf ?patient .
  ?patient gk:takesMedication ?first , ?second .
  ?first gk:drugClass ?a . ?second gk:drugClass ?b .
  ?interaction a gk:DrugInteraction ; gk:interactionBetween ?a , ?b ; gk:severity ?severity ; gk:reason ?why .
  FILTER(?a != ?b && STR(?first) < STR(?second))
  BIND(STRAFTER(STR(?first), "#") AS ?n1)
  BIND(STRAFTER(STR(?second), "#") AS ?n2)
  BIND(IRI(CONCAT(STR(?encounter), "_A_", ?n1, "_", ?n2)) AS ?alert)
  BIND(CONCAT(STRAFTER(STR(?encounter), "#"), " alert: ", ?n1, " with ", ?n2) AS ?label)
}"""),
    ("70-triage-emergency", "Triage: emergency",
     "The reasoner classified the encounter as EmergencyEncounter.", False, """
CONSTRUCT {
  ?d a gk:TriageDecision ; rdfs:label ?label ; gk:ofEncounter ?encounter ; gk:triageLevel gkd:Emergency ;
     gk:triggeredBy ?symptom ; gk:reason "An emergency warning sign was reported."@en .
}
WHERE {
  ?encounter a gk:EmergencyEncounter ; gk:showsSymptom ?symptom .
  ?symptom a gk:EmergencySymptom .
  BIND(IRI(CONCAT(STR(?encounter), "_T_Emergency")) AS ?d)
  BIND(CONCAT(STRAFTER(STR(?encounter), "#"), " triage: Emergency") AS ?label)
}"""),
    ("71-triage-urgent", "Triage: urgent",
     "An alarm symptom that is not an emergency symptom.", False, """
CONSTRUCT {
  ?d a gk:TriageDecision ; rdfs:label ?label ; gk:ofEncounter ?encounter ; gk:triageLevel gkd:Urgent ;
     gk:triggeredBy ?symptom ; gk:reason "A warning sign was reported."@en .
}
WHERE {
  ?encounter a gk:AlarmEncounter ; gk:showsSymptom ?symptom .
  ?symptom a gk:AlarmSymptom .
  FILTER NOT EXISTS { ?symptom a gk:EmergencySymptom }
  BIND(IRI(CONCAT(STR(?encounter), "_T_Urgent")) AS ?d)
  BIND(CONCAT(STRAFTER(STR(?encounter), "#"), " triage: Urgent") AS ?label)
}"""),
    ("72-triage-age", "Triage: referral by age",
     "Dyspeptic symptoms at or above the referral age (ACG/CAG guideline, conditional recommendation).",
     False, """
CONSTRUCT {
  ?d a gk:TriageDecision ; rdfs:label ?label ; gk:ofEncounter ?encounter ; gk:triageLevel gkd:Referral ;
     gk:triggeredBy gkd:Policy ; gk:reason "Dyspepsia at or above the endoscopy referral age."@en .
}
WHERE {
  gkd:Policy gk:referralAge ?threshold .
  ?encounter a gk:DyspepticEncounter ; gk:encounterOf ?patient .
  ?patient gk:age ?age .
  FILTER(?age >= ?threshold)
  BIND(IRI(CONCAT(STR(?encounter), "_T_Referral")) AS ?d)
  BIND(CONCAT(STRAFTER(STR(?encounter), "#"), " triage: Referral") AS ?label)
}"""),
    ("73-triage-primary-care", "Triage: primary care",
     "A supported hypothesis deserves a routine visit.", False, """
CONSTRUCT {
  ?d a gk:TriageDecision ; rdfs:label ?label ; gk:ofEncounter ?encounter ; gk:triageLevel gkd:PrimaryCare ;
     gk:triggeredBy ?h ; gk:reason "A disease hypothesis is supported by the reported symptoms."@en .
}
WHERE {
  ?encounter gk:primaryHypothesis ?h .
  BIND(IRI(CONCAT(STR(?encounter), "_T_PrimaryCare")) AS ?d)
  BIND(CONCAT(STRAFTER(STR(?encounter), "#"), " triage: Primary care") AS ?label)
}"""),
    ("74-triage-medication-review", "Triage: medication review",
     "A high-severity safety alert needs a clinician, even without a supported diagnosis.", False, """
CONSTRUCT {
  ?d a gk:TriageDecision ; rdfs:label ?label ; gk:ofEncounter ?encounter ; gk:triageLevel gkd:PrimaryCare ;
     gk:triggeredBy ?alert ; gk:reason "A high-severity medicine alert needs a medication review."@en .
}
WHERE {
  ?alert a gk:SafetyAlert ; gk:ofEncounter ?encounter ; gk:severity "high" .
  BIND(IRI(CONCAT(STR(?encounter), "_T_MedicationReview")) AS ?d)
  BIND(CONCAT(STRAFTER(STR(?encounter), "#"), " triage: Medication review") AS ?label)
}"""),
    ("75-triage-self-monitor", "Triage: self-monitor",
     "No other triage rule applied (negation as failure over the results above).", False, """
CONSTRUCT {
  ?d a gk:TriageDecision ; rdfs:label ?label ; gk:ofEncounter ?encounter ; gk:triageLevel gkd:SelfMonitor ;
     gk:reason "No warning sign and no supported hypothesis. Return if symptoms persist or worsen."@en .
}
WHERE {
  ?encounter a gk:Encounter .
  FILTER NOT EXISTS { ?x a gk:TriageDecision ; gk:ofEncounter ?encounter }
  BIND(IRI(CONCAT(STR(?encounter), "_T_SelfMonitor")) AS ?d)
  BIND(CONCAT(STRAFTER(STR(?encounter), "#"), " triage: Self-monitor") AS ?label)
}"""),
    ("76-triage-final", "Final triage level",
     "Keep the most urgent level, using the transitive property moreUrgentThan.", False, """
CONSTRUCT { ?encounter gk:finalTriage ?level }
WHERE {
  ?d a gk:TriageDecision ; gk:ofEncounter ?encounter ; gk:triageLevel ?level .
  FILTER NOT EXISTS {
    ?o a gk:TriageDecision ; gk:ofEncounter ?encounter ; gk:triageLevel ?higher .
    ?higher gk:moreUrgentThan ?level .
  }
}"""),
    ("90-recommendation-advice", "Recommendation: initial advice",
     "Advice and examinations for the primary hypothesis, unless the case is an emergency.", False, """
CONSTRUCT {
  ?r a gk:Recommendation ; rdfs:label ?label ; gk:ofEncounter ?encounter ; gk:forDisease ?disease ;
     gk:adviceText ?advice ; gk:recommendsExamination ?exam ; gk:triggeredBy ?h .
}
WHERE {
  ?encounter gk:primaryHypothesis ?h ; gk:finalTriage ?level .
  FILTER(?level != gkd:Emergency)
  ?h gk:forDisease ?disease .
  ?disease gk:initialAdvice ?advice ; gk:code ?dc .
  OPTIONAL { ?disease gk:suggestsExamination ?exam }
  BIND(IRI(CONCAT(STR(?encounter), "_R_", ?dc)) AS ?r)
  BIND(CONCAT(STRAFTER(STR(?encounter), "#"), " advice for ", STRAFTER(STR(?disease), "#")) AS ?label)
}"""),
    ("91-recommendation-hpylori", "Recommendation: test for H. pylori below the referral age",
     "ACG/CAG guideline: non-invasive H. pylori testing for dyspepsia under 60.", False, """
CONSTRUCT {
  ?r a gk:Recommendation ; rdfs:label ?label ; gk:ofEncounter ?encounter ;
     gk:recommendsExamination gkd:HPyloriTest ; gk:triggeredBy gkd:Policy ;
     gk:adviceText "Dyspepsia below the referral age: ask for a non-invasive H. pylori test."@en .
}
WHERE {
  gkd:Policy gk:referralAge ?threshold .
  ?encounter a gk:DyspepticEncounter ; gk:encounterOf ?patient ; gk:finalTriage ?level .
  ?patient gk:age ?age .
  FILTER(?age < ?threshold && ?level = gkd:PrimaryCare)
  BIND(IRI(CONCAT(STR(?encounter), "_R_HPylori")) AS ?r)
  BIND(CONCAT(STRAFTER(STR(?encounter), "#"), " advice: H. pylori test") AS ?label)
}"""),
    ("92-recommendation-endoscopy", "Recommendation: endoscopy at or above the referral age",
     "ACG/CAG guideline: endoscopy for dyspepsia at 60 or older.", False, """
CONSTRUCT {
  ?r a gk:Recommendation ; rdfs:label ?label ; gk:ofEncounter ?encounter ;
     gk:recommendsExamination gkd:UpperEndoscopy ; gk:triggeredBy gkd:Policy ;
     gk:adviceText "Dyspepsia at or above the referral age: discuss upper endoscopy."@en .
}
WHERE {
  gkd:Policy gk:referralAge ?threshold .
  ?encounter a gk:DyspepticEncounter ; gk:encounterOf ?patient ; gk:finalTriage ?level .
  ?patient gk:age ?age .
  FILTER(?age >= ?threshold && ?level != gkd:Emergency)
  BIND(IRI(CONCAT(STR(?encounter), "_R_Endoscopy")) AS ?r)
  BIND(CONCAT(STRAFTER(STR(?encounter), "#"), " advice: endoscopy") AS ?label)
}"""),
    ("95-next-question", "Backward chaining: candidate questions",
     "Unasked non-alarm symptoms that separate the two leading hypotheses (alarm symptoms are always screened). Score = difference of expert weights.",
     False, """
CONSTRUCT {
  ?q a gk:QuestionSuggestion ; rdfs:label ?label ; gk:ofEncounter ?encounter ; gk:askSymptom ?symptom ;
     gk:distinguishes ?h1 , ?h2 ; gk:discriminationScore ?score .
}
WHERE {
  ?h1 a gk:Hypothesis ; gk:ofEncounter ?encounter ; gk:rank 1 ; gk:forDisease ?d1 .
  ?h2 a gk:Hypothesis ; gk:ofEncounter ?encounter ; gk:rank 2 ; gk:forDisease ?d2 .
  ?encounter gk:finalTriage ?level . FILTER(?level != gkd:Emergency)
  ?link a gk:EvidenceLink ; gk:aboutSymptom ?symptom ; gk:ofDisease ?either .
  FILTER(?either = ?d1 || ?either = ?d2)
  FILTER NOT EXISTS { ?symptom a gk:AlarmSymptom }
  FILTER NOT EXISTS { ?encounter gk:hasObservation ?o . ?o gk:observedSymptom ?symptom }
  FILTER NOT EXISTS { ?encounter gk:hasObservation ?n . ?n gk:deniedSymptom ?symptom }
  OPTIONAL { ?l1 a gk:EvidenceLink ; gk:ofDisease ?d1 ; gk:aboutSymptom ?symptom ; gk:expertCF ?w1 }
  OPTIONAL { ?l2 a gk:EvidenceLink ; gk:ofDisease ?d2 ; gk:aboutSymptom ?symptom ; gk:expertCF ?w2 }
  BIND(ABS(COALESCE(?w1, 0.0) - COALESCE(?w2, 0.0)) AS ?score)
  ?symptom gk:code ?sc .
  BIND(IRI(CONCAT(STR(?encounter), "_Q_", ?sc)) AS ?q)
  BIND(CONCAT(STRAFTER(STR(?encounter), "#"), " ask about ", ?sc) AS ?label)
}"""),
    ("96-best-question", "Backward chaining: best next question",
     "The candidate with the highest score (ties broken by symptom code).", False, """
CONSTRUCT { ?q gk:rank 1 }
WHERE {
  ?q a gk:QuestionSuggestion ; gk:ofEncounter ?encounter ; gk:discriminationScore ?score ; gk:askSymptom ?s .
  ?s gk:code ?code .
  FILTER NOT EXISTS {
    ?o a gk:QuestionSuggestion ; gk:ofEncounter ?encounter ; gk:discriminationScore ?score2 ; gk:askSymptom ?s2 .
    ?s2 gk:code ?code2 .
    FILTER(?score2 > ?score || (?score2 = ?score && ?code2 < ?code))
  }
}"""),
]

if __name__ == "__main__":
    RULES.mkdir(exist_ok=True)
    for old in RULES.glob("*.rq"):
        old.unlink()
    for name, title, description, repeat, body in DEFINITIONS:
        header = f"# title: {title}\n# description: {description}\n# iterate: {'true' if repeat else 'false'}\n"
        (RULES / f"{name}.rq").write_text(header + PREFIXES + body.strip() + "\n", encoding="utf-8")
    print(f"written {len(DEFINITIONS)} rules to {RULES}")
