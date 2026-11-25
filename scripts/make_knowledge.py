"""Generate the two A-Box files from compact tables.

ontology/gastrokg-knowledge.ttl  expert knowledge (diseases, symptoms, weights, rules, drugs)
ontology/gastrokg-cases.ttl      synthetic patient cases

Run:  python scripts/make_knowledge.py
Edit the tables below, not the generated files.
"""
from pathlib import Path

ONTOLOGY = Path(__file__).resolve().parent.parent / "ontology"

NIDDK = "https://www.niddk.nih.gov/health-information/digestive-diseases/"
SOURCES = {
    "gastritis": NIDDK + "gastritis-gastropathy/symptoms-causes",
    "dyspepsia": NIDDK + "indigestion-dyspepsia/symptoms-causes",
    "gerd": NIDDK + "acid-reflux-ger-gerd-adults/symptoms-causes",
    "ulcer": NIDDK + "peptic-ulcers-stomach-ulcers/symptoms-causes",
    "gastroparesis": NIDDK + "gastroparesis/symptoms-causes",
    "cancer": "https://www.cancer.gov/types/stomach/symptoms",
    "acg": "https://pubmed.ncbi.nlm.nih.gov/28631728/",
    "nhs_nsaid": "https://www.nhs.uk/medicines/nsaids/",
    "nhs_ibuprofen": "https://www.nhs.uk/medicines/ibuprofen-for-adults/",
    "nhs_warfarin": "https://www.nhs.uk/medicines/warfarin/",
}
SOURCE_TITLES = {
    "gastritis": "NIDDK: Symptoms and causes of gastritis and gastropathy",
    "dyspepsia": "NIDDK: Symptoms and causes of indigestion",
    "gerd": "NIDDK: Symptoms and causes of GER and GERD",
    "ulcer": "NIDDK: Symptoms and causes of peptic ulcers",
    "gastroparesis": "NIDDK: Symptoms and causes of gastroparesis",
    "cancer": "NCI: Stomach cancer symptoms",
    "acg": "Moayyedi et al. (2017). ACG and CAG clinical guideline: management of dyspepsia",
    "nhs_nsaid": "NHS: NSAIDs",
    "nhs_ibuprofen": "NHS: Ibuprofen for adults",
    "nhs_warfarin": "NHS: Warfarin",
}
GROUP = "gkd:GroupAssignment"   # our earlier slides, or our own modelling choice

# code, local name, English, Indonesian, classes, lay synonyms (id/en)
SYMPTOMS = [
    ("G01", "EpigastricPain", "Epigastric pain or soreness", "Nyeri atau perih ulu hati",
     ["DyspepticSymptom"], ["ulu hati perih", "sakit ulu hati", "nyeri lambung", "upper stomach pain"]),
    ("G02", "Nausea", "Nausea and urge to vomit", "Mual dan ingin muntah",
     ["DyspepticSymptom"], ["mual", "enek", "eneg", "feeling sick"]),
    ("G03", "Bloating", "Bloating or fullness", "Perut kembung atau terasa penuh",
     ["DyspepticSymptom"], ["kembung", "begah", "perut penuh"]),
    ("G04", "Heartburn", "Burning sensation in the chest (heartburn)", "Rasa panas di dada",
     ["RefluxSymptom"], ["dada panas", "dada terbakar", "heartburn"]),
    ("G05", "Belching", "Frequent belching", "Sering sendawa",
     ["DyspepticSymptom"], ["sendawa", "glegekan", "burping"]),
    ("G06", "EarlySatiety", "Early satiety when eating", "Cepat kenyang saat makan",
     ["DyspepticSymptom"], ["cepat kenyang", "baru makan sudah kenyang"]),
    ("G07", "SourTaste", "Sour vomit or bitter taste in the mouth", "Mulut asam atau pahit",
     ["RefluxSymptom"], ["mulut pahit", "mulut asam"]),
    ("G08", "Regurgitation", "Regurgitation of food or fluid", "Makanan atau cairan naik kembali",
     ["RefluxSymptom"], ["asam lambung naik", "makanan naik lagi", "acid coming up"]),
    ("G09", "CoughHoarseness", "Chronic cough or hoarseness", "Batuk lama atau suara serak",
     ["RefluxSymptom"], ["batuk lama", "suara serak"]),
    ("G10", "HungerNightPain", "Upper abdominal pain on an empty stomach or at night",
     "Nyeri ulu hati saat perut kosong atau malam hari",
     ["DyspepticSymptom"], ["perih saat lapar", "terbangun malam karena perih"]),
    ("G11", "Vomiting", "Vomiting", "Muntah", ["DyspepticSymptom"], ["muntah", "throwing up"]),
    ("G12", "ProlongedFullness", "Feeling full long after a meal", "Kenyang lama setelah makan",
     ["DyspepticSymptom"], ["kenyang terus", "makanan lama turun"]),
    ("G13", "AppetiteLoss", "Loss of appetite", "Nafsu makan menurun",
     ["DyspepticSymptom"], ["tidak nafsu makan", "malas makan"]),
    ("A01", "VomitingBlood", "Vomiting blood or coffee-ground material", "Muntah darah atau seperti ampas kopi",
     ["BleedingSymptom"], ["muntah darah", "hematemesis"]),
    ("A02", "BlackStool", "Black, tarry or bloody stool", "BAB hitam seperti aspal atau berdarah",
     ["BleedingSymptom"], ["bab hitam", "berak darah", "melena"]),
    ("A03", "WeightLoss", "Unintentional weight loss", "Berat badan turun tanpa sebab",
     ["AlarmSymptom"], ["berat badan turun", "makin kurus"]),
    ("A04", "Dysphagia", "Difficult or painful swallowing", "Sulit atau nyeri menelan",
     ["AlarmSymptom"], ["susah menelan", "sakit menelan", "disfagia"]),
    ("A05", "PersistentVomiting", "Persistent or frequent vomiting", "Muntah terus-menerus",
     ["AlarmSymptom"], ["muntah terus"]),
    ("A06", "SevereAbdominalPain", "Sudden, severe or constant abdominal pain", "Nyeri perut hebat mendadak atau menetap",
     ["EmergencySymptom"], ["perut sakit sekali", "nyeri hebat"]),
    ("A07", "Fainting", "Fainting, dizziness or rapid pulse", "Pingsan, pusing berat atau nadi cepat",
     ["EmergencySymptom"], ["pingsan", "mau pingsan"]),
    ("A08", "Jaundice", "Yellow eyes or skin", "Mata atau kulit kuning",
     ["AlarmSymptom"], ["mata kuning", "jaundice"]),
    ("A09", "ChestJawArmPain", "Pain in the chest, jaw, neck or arm", "Nyeri dada, rahang, leher atau lengan",
     ["EmergencySymptom"], ["nyeri dada", "chest pain"]),
]

# local name, code, English, Indonesian, class, ICD-10, matches, anatomy, exams, advice
DISEASES = [
    ("Gastritis", "P01", "Gastritis (acute)", "Gastritis (akut)", "InflammatoryDisease", "K29.1",
     [("broadMatch", "wd:Q183130"), ("broadMatch", "obo:DOID_4029")], "StomachLining", ["HPyloriTest"],
     "Avoid alcohol and anti-inflammatory painkillers until a clinician has reviewed the complaint."),
    ("Dyspepsia", "P02", "Dyspepsia (functional)", "Dispepsia (fungsional)", "FunctionalDisorder", "K30",
     [("closeMatch", "wd:Q653971")], "UpperGITract", ["HPyloriTest"],
     "Note the foods that trigger symptoms, eat smaller meals and return if symptoms persist."),
    ("GERD", "P03", "GERD (gastroesophageal reflux disease)", "GERD (penyakit refluks gastroesofagus)",
     "RefluxDisease", "K21",
     [("exactMatch", "wd:Q223591"), ("exactMatch", "obo:DOID_8534")], "Esophagus", ["PHMonitoring"],
     "Avoid lying down soon after meals, raise the head of the bed and discuss acid suppression with a clinician."),
    ("PepticUlcer", "P04", "Peptic (stomach) ulcer", "Tukak lambung", "UlcerDisease", "K25",
     [("broadMatch", "wd:Q172941"), ("broadMatch", "obo:DOID_750")], "StomachLining",
     ["HPyloriTest", "UpperEndoscopy"],
     "See a clinician for H. pylori testing and a review of painkiller use."),
    ("Gastroparesis", "P05", "Gastroparesis", "Gastroparesis", "MotilityDisorder", "K31.8",
     [("exactMatch", "wd:Q943897")], "Stomach", ["GastricEmptyingStudy"],
     "Eat small frequent meals, check blood glucose if diabetic and ask for a gastric emptying assessment."),
    ("StomachCancer", "P06", "Stomach cancer", "Kanker lambung", "MalignantNeoplasm", "C16",
     [("exactMatch", "wd:Q189588")], "Stomach", ["UpperEndoscopy", "CompleteBloodCount"],
     "This screen cannot confirm or exclude cancer. Arrange a specialist assessment."),
]

# (disease code, symptom code, CF when present, CF when denied or None, source key or None)
# source None = the association comes from our group assignment or is our own modelling choice
EVIDENCE = [
    ("P01", "G01", 0.8, -0.3, "gastritis"), ("P01", "G02", 0.6, None, "gastritis"),
    ("P01", "G03", 0.4, None, "gastritis"), ("P01", "G06", 0.3, None, "gastritis"),
    ("P01", "G13", 0.3, None, "gastritis"),

    ("P02", "G01", 0.6, -0.3, "dyspepsia"), ("P02", "G02", 0.3, None, "dyspepsia"),
    ("P02", "G03", 0.7, None, "dyspepsia"), ("P02", "G05", 0.4, None, "dyspepsia"),
    ("P02", "G06", 0.7, None, "dyspepsia"),
    ("P02", "A02", -0.6, None, None), ("P02", "A03", -0.5, None, None), ("P02", "A05", -0.4, None, None),

    ("P03", "G01", 0.8, None, None), ("P03", "G02", 0.6, None, "gerd"),
    ("P03", "G04", 0.8, -0.4, "gerd"), ("P03", "G07", 0.6, None, None),
    ("P03", "G08", 0.8, -0.2, "gerd"), ("P03", "G09", 0.3, None, "gerd"),

    ("P04", "G01", 0.7, -0.3, "ulcer"), ("P04", "G02", 0.3, None, "ulcer"),
    ("P04", "G03", 0.3, None, "ulcer"), ("P04", "G05", 0.2, None, "ulcer"),
    ("P04", "G06", 0.2, None, "ulcer"), ("P04", "G10", 0.8, -0.3, "ulcer"),
    ("P04", "A01", 0.6, None, "ulcer"), ("P04", "A02", 0.6, None, "ulcer"),

    ("P05", "G01", 0.2, None, "gastroparesis"), ("P05", "G02", 0.5, None, "gastroparesis"),
    ("P05", "G03", 0.5, None, "gastroparesis"), ("P05", "G04", 0.2, None, "gastroparesis"),
    ("P05", "G05", 0.2, None, "gastroparesis"), ("P05", "G06", 0.7, -0.4, "gastroparesis"),
    ("P05", "G11", 0.6, None, "gastroparesis"), ("P05", "G12", 0.8, -0.3, "gastroparesis"),
    ("P05", "G13", 0.3, None, "gastroparesis"),

    ("P06", "G01", 0.2, None, "cancer"), ("P06", "G02", 0.1, None, "cancer"),
    ("P06", "G03", 0.2, None, "cancer"), ("P06", "G04", 0.1, None, "cancer"),
    ("P06", "G11", 0.2, None, "cancer"), ("P06", "G13", 0.4, None, "cancer"),
    ("P06", "A02", 0.4, None, "cancer"), ("P06", "A03", 0.6, -0.3, "cancer"),
    ("P06", "A04", 0.5, None, "cancer"),
]
# weights printed on the group-assignment slides
SLIDE_WEIGHTS = {("P03", "G01"), ("P03", "G02"), ("P03", "G04"), ("P03", "G07")}

RULES = [
    ("R1", "P01", ["G01", "G02", "G03"], None),
    ("R2", "P02", ["G01", "G03", "G05", "G06"], None),
    ("R3", "P03", ["G01", "G02", "G04", "G07"], None),
    ("R4", "P04", ["G01", "G02", "G10"], "ulcer"),
    ("R5", "P05", ["G02", "G06", "G12"], "gastroparesis"),
    ("R6", "P06", ["A03", "G01", "G13"], "cancer"),
    ("R7", "P03", ["G04", "G08"], "gerd"),
]

RISKS = [
    ("HPyloriInfection", "History of H. pylori infection", "Riwayat infeksi H. pylori",
     [("Gastritis", "gastritis"), ("PepticUlcer", "ulcer"), ("Dyspepsia", "dyspepsia")]),
    ("Smoking", "Smoking", "Merokok", [("GERD", "gerd")]),
    ("Obesity", "Overweight or obesity", "Kelebihan berat badan", [("GERD", "gerd")]),
    ("Pregnancy", "Pregnancy", "Kehamilan", [("GERD", "gerd")]),
    ("AlcoholUse", "Alcohol use", "Konsumsi alkohol", [("Gastritis", "gastritis")]),
    ("Diabetes", "Diabetes", "Diabetes", [("Gastroparesis", "gastroparesis")]),
]

DRUG_CLASSES = [
    ("NSAID", "Non-steroidal anti-inflammatory drug (NSAID)", "Obat antiinflamasi nonsteroid", ["Paracetamol"]),
    ("Anticoagulant", "Anticoagulant", "Antikoagulan (pengencer darah)", []),
    ("Corticosteroid", "Corticosteroid", "Kortikosteroid", []),
    ("Opioid", "Opioid pain medicine", "Obat nyeri golongan opioid", ["Paracetamol"]),
    ("NonOpioidAnalgesic", "Non-opioid analgesic", "Analgesik non-opioid", []),
]
MEDICATIONS = [
    ("Ibuprofen", "Ibuprofen", "NSAID"), ("Naproxen", "Naproxen", "NSAID"), ("Aspirin", "Aspirin", "NSAID"),
    ("Warfarin", "Warfarin", "Anticoagulant"), ("Prednisone", "Prednisone", "Corticosteroid"),
    ("Morphine", "Morphine", "Opioid"), ("Codeine", "Codeine", "Opioid"),
    ("Paracetamol", "Paracetamol", "NonOpioidAnalgesic"),
]
CAUTIONS = [
    ("NSAID", "PepticUlcer", "high", ["ulcer", "nhs_ibuprofen"],
     "NSAIDs are a common cause of peptic ulcers."),
    ("NSAID", "Gastritis", "high", ["gastritis"], "Long-term NSAID use can injure the stomach lining."),
    ("NSAID", "GERD", "moderate", ["gerd"], "NSAIDs can cause or worsen reflux disease."),
    ("NSAID", "Dyspepsia", "moderate", ["dyspepsia"], "NSAIDs can cause indigestion."),
    ("Corticosteroid", "Dyspepsia", "moderate", ["dyspepsia"], "Corticosteroids can cause indigestion."),
    ("Opioid", "Gastroparesis", "high", ["gastroparesis"],
     "Opioid pain medicines can delay stomach emptying or worsen symptoms."),
]
INTERACTIONS = [
    ("NSAID", "Anticoagulant", "high", ["nhs_nsaid", "nhs_warfarin"],
     "Taking an NSAID with an anticoagulant raises the risk of bleeding."),
    ("NSAID", "Corticosteroid", "high", ["ulcer"],
     "Corticosteroids taken with NSAIDs raise the risk of peptic ulcer."),
]

# code, title, age, observed {symptom: certainty}, denied, risk factors, medications
CASES = [
    ("E001", "Worked example from our slides", 34,
     {"G01": 1.0, "G02": 0.8, "G04": 1.0, "G07": 0.6}, {}, [], []),
    ("E002", "Full gastritis rule", 28, {"G01": 0.8, "G02": 0.8, "G03": 0.6}, {}, ["AlcoholUse"], []),
    ("E003", "Three of four dyspepsia conditions", 41, {"G01": 0.6, "G03": 0.8, "G06": 0.8}, {}, [], []),
    ("E004", "Vomiting blood", 52, {"A01": 1.0, "G01": 0.8}, {}, ["HPyloriInfection"], []),
    ("E005", "Weight loss with swallowing difficulty", 49, {"A03": 0.8, "A04": 0.8, "G13": 0.6}, {}, [], []),
    ("E006", "New dyspepsia at 67", 67, {"G01": 0.8, "G03": 0.6}, {}, [], []),
    ("E007", "Ulcer pattern while taking ibuprofen", 45,
     {"G01": 1.0, "G02": 0.6, "G10": 0.8}, {}, [], ["Ibuprofen"]),
    ("E008", "Aspirin together with warfarin", 58, {"G01": 0.6}, {}, [], ["Aspirin", "Warfarin"]),
    ("E009", "Diabetes, morphine and slow emptying", 55,
     {"G02": 0.6, "G06": 0.8, "G11": 0.6, "G12": 0.8}, {}, ["Diabetes"], ["Morphine"]),
    ("E010", "One mild complaint", 23, {"G05": 0.4}, {}, [], []),
    ("E011", "Reflux symptoms denied", 36, {"G01": 0.8, "G02": 0.6}, {"G04": 1.0, "G08": 0.8}, [], []),
    ("E012", "Ambiguous early complaint", 31, {"G01": 0.8, "G03": 0.6}, {}, [], []),
    ("E013", "Chest pain that may not be the stomach", 50, {"A09": 0.8, "G04": 0.8}, {}, ["Smoking"], []),
]

PREFIXES = """@prefix gk:      <http://example.org/gastrokg/ontology#> .
@prefix gkd:     <http://example.org/gastrokg/data#> .
@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl:     <http://www.w3.org/2002/07/owl#> .
@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .
@prefix skos:    <http://www.w3.org/2004/02/skos/core#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix wd:      <http://www.wikidata.org/entity/> .
@prefix obo:     <http://purl.obolibrary.org/obo/> .
"""

SYMPTOM_NAME = {row[0]: row[1] for row in SYMPTOMS}
SYMPTOM_LABEL = {row[0]: row[2] for row in SYMPTOMS}
DISEASE_NAME = {row[1]: row[0] for row in DISEASES}
DISEASE_LABEL = {row[1]: row[2] for row in DISEASES}


def src(key):
    return GROUP if key is None else f"<{SOURCES[key]}>"


def labelled(subject, kind, en, id_=None, extra=()):
    labels = f'"{en}"@en' + (f' , "{id_}"@id' if id_ else "")
    lines = [f"{subject} a {kind}", f"    rdfs:label {labels}"] + [f"    {e}" for e in extra]
    return " ;\n".join(lines) + " .\n"


def knowledge():
    out = [
        "# GastroKG A-Box: expert knowledge. GENERATED by scripts/make_knowledge.py",
        "# Associations cite a public health source where it lists them. Every numeric",
        "# weight is illustrative and has NOT been clinically validated.",
        PREFIXES,
        "<http://example.org/gastrokg/knowledge> a owl:Ontology ;",
        '    rdfs:label "GastroKG knowledge base"@en ;',
        "    owl:imports <http://example.org/gastrokg/ontology> .\n",
        "# ---- Sources ----",
    ]
    out += [labelled(f"<{url}>", "dcterms:BibliographicResource", SOURCE_TITLES[k]) for k, url in SOURCES.items()]
    out.append(labelled(GROUP, "dcterms:BibliographicResource",
                        "Group assignment slides and modelling choices (Expert System for Stomach Disease Diagnosis, 2026)"))
    out.append("# ---- Controlled individuals ----")
    out.append(labelled("gkd:SlideWeight", "gk:WeightStatus", "Illustrative, carried over from our group assignment"))
    out.append(labelled("gkd:NewWeight", "gk:WeightStatus", "Illustrative, added for the final project"))
    for name, en, id_, prio in [("FullRuleMatch", "Full rule match", "Aturan terpenuhi", 3),
                                ("PartialMatch", "Partial match", "Cocok sebagian", 2),
                                ("WeakMatch", "Weak match", "Bukti lemah", 1)]:
        out.append(labelled(f"gkd:{name}", "gk:MatchStatus", en, id_, [f"gk:priority {prio}"]))
    out.append(labelled("gkd:Support", "gk:Polarity", "Supports", "Mendukung"))
    out.append(labelled("gkd:Oppose", "gk:Polarity", "Opposes", "Melawan"))

    out.append("# ---- Care facilities and triage levels ----")
    for name, en, id_ in [("PrimaryCareFacility", "Primary care (FKTP)", "Fasilitas kesehatan tingkat pertama"),
                          ("SpecialistClinic", "Specialist clinic with endoscopy", "Klinik spesialis dengan endoskopi"),
                          ("EmergencyDepartment", "Emergency department", "Instalasi gawat darurat (IGD)"),
                          ("HomeCare", "Self-care at home", "Perawatan mandiri di rumah")]:
        out.append(labelled(f"gkd:{name}", "gk:CareFacility", en, id_))
    levels = [("Emergency", "Emergency: go now", "Gawat darurat", 4, "Urgent", "EmergencyDepartment"),
              ("Urgent", "Urgent: see a doctor promptly", "Segera ke dokter", 3, "Referral", "PrimaryCareFacility"),
              ("Referral", "Referral for endoscopy", "Rujukan endoskopi", 2, "PrimaryCare", "SpecialistClinic"),
              ("PrimaryCare", "Routine primary care visit", "Kunjungan FKTP rutin", 1, "SelfMonitor", "PrimaryCareFacility"),
              ("SelfMonitor", "Self-monitor", "Pantau mandiri", 0, None, "HomeCare")]
    for name, en, id_, prio, below, place in levels:
        extra = [f"gk:priority {prio}", f"gk:refersTo gkd:{place}"]
        if below:
            extra.append(f"gk:moreUrgentThan gkd:{below}")
        out.append(labelled(f"gkd:{name}", "gk:TriageLevel", en, id_, extra))
    out.append("gkd:Emergency a gk:TriageLevel .\n"
               "[ a owl:AllDifferent ; owl:distinctMembers "
               "( gkd:Emergency gkd:Urgent gkd:Referral gkd:PrimaryCare gkd:SelfMonitor ) ] .\n")
    out.append(labelled("gkd:Policy", "gk:TriagePolicy", "Screening policy thresholds", None, [
        "gk:referralAge 60", "gk:partialMinSymptoms 2", "gk:partialMinCoverage 0.5", "gk:alertMinCF 0.5",
        f"dcterms:source <{SOURCES['acg']}> , {GROUP}",
        'rdfs:comment "Referral age 60 follows the ACG/CAG dyspepsia guideline (a conditional recommendation). The other thresholds are our modelling choices."@en']))

    out.append("# ---- Anatomy (partOf is transitive) ----")
    for name, en, parent in [("DigestiveSystem", "Digestive system", None),
                             ("UpperGITract", "Upper gastrointestinal tract", "DigestiveSystem"),
                             ("Esophagus", "Esophagus", "UpperGITract"), ("Stomach", "Stomach", "UpperGITract"),
                             ("StomachLining", "Stomach lining", "Stomach")]:
        out.append(labelled(f"gkd:{name}", "gk:AnatomicalSite", en, None,
                            [f"gk:partOf gkd:{parent}"] if parent else []))

    out.append("# ---- Examinations ----")
    for name, en in [("UpperEndoscopy", "Upper gastrointestinal endoscopy"), ("HPyloriTest", "Non-invasive H. pylori test"),
                     ("GastricEmptyingStudy", "Gastric emptying study"), ("PHMonitoring", "Esophageal pH monitoring"),
                     ("CompleteBloodCount", "Complete blood count")]:
        out.append(labelled(f"gkd:{name}", "gk:Examination", en))

    out.append("# ---- Symptoms ----")
    for code, name, en, id_, classes, synonyms in SYMPTOMS:
        alt = " , ".join(f'"{s}"' for s in synonyms)
        out.append(labelled(f"gkd:{name}", " , ".join(f"gk:{c}" for c in classes), en, id_,
                            [f'gk:code "{code}"', f"skos:altLabel {alt}"]))

    out.append("# ---- Diseases ----")
    for name, code, en, id_, cls, icd, matches, site, exams, advice in DISEASES:
        extra = [f'gk:code "{code}"', f'gk:icd10Code "{icd}"', f"gk:affects gkd:{site}",
                 "gk:suggestsExamination " + " , ".join(f"gkd:{e}" for e in exams),
                 f'gk:initialAdvice "{advice}"@en']
        extra += [f"skos:{rel} {target}" for rel, target in matches]
        out.append(labelled(f"gkd:{name}", f"gk:{cls}", en, id_, extra))
    out.append("[ a owl:AllDifferent ; owl:distinctMembers ( "
               + " ".join(f"gkd:{d[0]}" for d in DISEASES) + " ) ] .\n")

    out.append("# ---- Evidence links (expert certainty factors) ----")
    for disease, symptom, cf, absent, source in EVIDENCE:
        status = "SlideWeight" if (disease, symptom) in SLIDE_WEIGHTS else "NewWeight"
        extra = [f"gk:ofDisease gkd:{DISEASE_NAME[disease]}", f"gk:aboutSymptom gkd:{SYMPTOM_NAME[symptom]}",
                 f"gk:expertCF {cf}"]
        if absent is not None:
            extra.append(f"gk:absenceCF {absent}")
        extra += [f"gk:weightStatus gkd:{status}", f"dcterms:source {src(source)}"]
        label = f"{SYMPTOM_LABEL[symptom]} / {DISEASE_LABEL[disease]} (CF {cf})"
        out.append(labelled(f"gkd:EL_{disease}_{symptom}", "gk:EvidenceLink", label, None, extra))

    out.append("# ---- IF-THEN diagnostic rules ----")
    for rule, disease, needs, source in RULES:
        label = f"{rule}: IF {' AND '.join(needs)} THEN {DISEASE_NAME[disease]}"
        out.append(labelled(f"gkd:{rule}", "gk:DiagnosticRule", label, None, [
            f'gk:code "{rule}"', f"gk:concludes gkd:{DISEASE_NAME[disease]}",
            "gk:requiresSymptom " + " , ".join(f"gkd:{SYMPTOM_NAME[s]}" for s in needs),
            f"dcterms:source {src(source)}"]))

    out.append("# ---- Risk factors ----")
    for name, en, id_, links in RISKS:
        out.append(labelled(f"gkd:{name}", "gk:RiskFactor", en, id_, [
            "gk:increasesRiskOf " + " , ".join(f"gkd:{d}" for d, _ in links),
            "dcterms:source " + " , ".join(dict.fromkeys(src(s) for _, s in links))]))

    out.append("# ---- Medicines and safety knowledge ----")
    for name, en, id_, alternatives in DRUG_CLASSES:
        extra = [f"gk:saferAlternative gkd:{a}" for a in alternatives]
        out.append(labelled(f"gkd:{name}", "gk:DrugClass", en, id_, extra))
    for name, en, cls in MEDICATIONS:
        out.append(labelled(f"gkd:{name}", "gk:Medication", en, None, [f"gk:drugClass gkd:{cls}"]))
    for n, (cls, disease, severity, sources, why) in enumerate(CAUTIONS, 1):
        out.append(labelled(f"gkd:DC{n}", "gk:DrugCaution", f"Caution: {cls} in {disease}", None, [
            f"gk:cautionDrugClass gkd:{cls}", f"gk:cautionDisease gkd:{disease}", f'gk:severity "{severity}"',
            f'gk:reason "{why}"@en', "dcterms:source " + " , ".join(src(s) for s in sources)]))
    for n, (a, b, severity, sources, why) in enumerate(INTERACTIONS, 1):
        out.append(labelled(f"gkd:DI{n}", "gk:DrugInteraction", f"Interaction: {a} with {b}", None, [
            f"gk:interactionBetween gkd:{a} , gkd:{b}", f'gk:severity "{severity}"',
            f'gk:reason "{why}"@en', "dcterms:source " + " , ".join(src(s) for s in sources)]))
    return "\n".join(out)


def cases():
    out = ["# GastroKG A-Box: SYNTHETIC patient cases. GENERATED by scripts/make_knowledge.py",
           "# No real patient data.", PREFIXES]
    for code, title, age, observed, denied, risks, meds in CASES:
        patient = code.replace("E", "PT")
        extra = [f"gk:age {age}", f"gk:hadEncounter gkd:{code}"]
        if risks:
            extra.append("gk:hasRiskFactor " + " , ".join(f"gkd:{r}" for r in risks))
        if meds:
            extra.append("gk:takesRegularly " + " , ".join(f"gkd:{m}" for m in meds))
        out.append(f"# ---- {code}: {title} ----")
        out.append(labelled(f"gkd:{patient}", "gk:Patient", f"Synthetic patient {patient} ({age} y)", None, extra))
        observations = [(s, cf, "observedSymptom", "has") for s, cf in observed.items()]
        observations += [(s, cf, "deniedSymptom", "denies") for s, cf in denied.items()]
        ids = " , ".join(f"gkd:{code}_obs_{s}" for s, *_ in observations)
        out.append(labelled(f"gkd:{code}", "gk:Encounter", f"{code}: {title}", None, [f"gk:hasObservation {ids}"]))
        for symptom, cf, prop, verb in observations:
            out.append(labelled(f"gkd:{code}_obs_{symptom}", "gk:SymptomObservation",
                                f"{code} {verb} {SYMPTOM_LABEL[symptom].lower()} ({cf})", None,
                                [f"gk:{prop} gkd:{SYMPTOM_NAME[symptom]}", f"gk:userCF {cf}"]))
    return "\n".join(out)


if __name__ == "__main__":
    (ONTOLOGY / "gastrokg-knowledge.ttl").write_text(knowledge(), encoding="utf-8")
    (ONTOLOGY / "gastrokg-cases.ttl").write_text(cases(), encoding="utf-8")
    print("written:", ONTOLOGY)
