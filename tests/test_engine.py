"""Behaviour of the knowledge graph: competency questions, rules, shapes."""
from decimal import Decimal
from pathlib import Path

import pytest
from rdflib import Literal
from rdflib.namespace import RDF

from backend.app import engine
from backend.app.engine import GK, GKD

QUERIES = Path(__file__).resolve().parent.parent / "graphdb" / "queries"


@pytest.fixture(scope="session")
def result():
    return engine.reason_all_cases()


def ask(result, name):
    """Run a stored competency question and return plain Python rows."""
    query = next(QUERIES.glob(f"{name}*.rq")).read_text(encoding="utf-8")
    return [tuple(None if v is None else v.toPython() for v in row) for row in result.graph.query(query)]


# ---------------------------------------------------------------- competency questions
def test_cq01_epigastric_pain(result):
    assert [r[0] for r in ask(result, "cq01")] == ["P01", "P02", "P03", "P04", "P05", "P06"]


def test_cq02_emergency_symptoms_include_bleeding_by_subclass(result):
    assert [r[0] for r in ask(result, "cq02")] == ["A01", "A02", "A06", "A07", "A09"]


def test_cq03_anatomy_chain(result):
    assert [r[0] for r in ask(result, "cq03")] == ["P01", "P02", "P03", "P04", "P05", "P06"]


def test_cq04_differential_diagnosis(result):
    rows = ask(result, "cq04")
    assert rows[0][:2] == (1, "P03") and rows[0][3] == "FullRuleMatch"
    assert [r[0] for r in rows] == list(range(1, len(rows) + 1))


def test_cq05_reproduces_the_worked_example_of_the_previous_project(result):
    rows = ask(result, "cq05")
    assert [r[1] for r in rows] == ["G01", "G02", "G04", "G07"]
    assert [r[4] for r in rows] == [Decimal("0.8"), Decimal("0.896"), Decimal("0.9792"), Decimal("0.986688")]


def test_cq06_three_of_four_conditions_is_no_longer_silent(result):
    assert ("P02", Decimal("0.75"), "G05") in ask(result, "cq06")


def test_cq07_emergencies(result):
    assert ask(result, "cq07") == [("E004", "A01"), ("E013", "A09")]


TRIAGE = {
    "E001": "PrimaryCare", "E002": "PrimaryCare", "E003": "PrimaryCare", "E004": "Emergency",
    "E005": "Urgent", "E006": "Referral", "E007": "PrimaryCare", "E008": "PrimaryCare",
    "E009": "PrimaryCare", "E010": "SelfMonitor", "E011": "PrimaryCare", "E012": "PrimaryCare",
    "E013": "Emergency",
}


def test_cq08_exactly_one_final_triage_per_encounter(result):
    rows = ask(result, "cq08")
    assert len(rows) == len(TRIAGE)
    assert {r[0]: r[1] for r in rows} == TRIAGE


def test_cq09_nsaid_users_are_classified_by_owl(result):
    assert ask(result, "cq09") == [("PT007",), ("PT008",)]


def test_cq10_safety_alerts(result):
    alerts = {(r[0], r[1], r[2]) for r in ask(result, "cq10")}
    assert ("E007", "Ibuprofen", "high") in alerts
    assert ("E008", "Aspirin", "high") in alerts and ("E008", "Warfarin", "high") in alerts
    assert ("E009", "Morphine", "high") in alerts
    assert {a[0] for a in alerts} == {"E007", "E008", "E009"}


def test_cq11_next_question(result):
    questions = {r[0]: r[1] for r in ask(result, "cq11")}
    assert questions["E001"] == "G08"
    assert not {"E004", "E013"} & questions.keys(), "emergencies are referred, not questioned"
    assert all(code.startswith("G") for code in questions.values()), "alarm symptoms are screened separately"


def test_cq12_every_weight_is_declared_illustrative(result):
    assert {r[0] for r in ask(result, "cq12")} == {"SlideWeight", "NewWeight"}


def test_cq13_denied_symptoms_lower_the_certainty(result):
    rows = ask(result, "cq13")
    assert ("P03", "G04", Decimal("-0.4")) in rows and ("P03", "G08", Decimal("-0.16")) in rows
    cf = result.graph.value(GKD.E011_P03, GK.certaintyFactor).toPython()
    # support 0.7696, opposition -0.496 -> (0.7696 - 0.496) / (1 - 0.496)
    assert abs(cf - Decimal("0.2736") / Decimal("0.504")) < Decimal("1e-12")


def test_cq14_union_class(result):
    assert ask(result, "cq14") == [("PT004",), ("PT007",), ("PT008",)]


# ---------------------------------------------------------------- reasoning details
def test_strict_rule_does_not_fire_with_a_missing_condition(result):
    assert (GKD.E003_R2, RDF.type, GK.RuleFiring) not in result.graph
    assert (GKD.E001_R3, RDF.type, GK.RuleFiring) in result.graph


def test_alarm_classification_comes_from_owl_not_from_the_data(result):
    asserted = engine.load_graph(engine.CASES)
    assert (GKD.E004, RDF.type, GK.EmergencyEncounter) not in asserted
    assert (GKD.E004, RDF.type, GK.EmergencyEncounter) in result.graph
    assert (GKD.E005, RDF.type, GK.AlarmEncounter) in result.graph
    assert (GKD.E005, RDF.type, GK.EmergencyEncounter) not in result.graph


def test_every_certainty_factor_is_in_range(result):
    values = [v.toPython() for v in result.graph.objects(None, GK.certaintyFactor)]
    assert values and all(-1 < v < 1 for v in values)


def test_disabling_the_age_rule_changes_only_the_age_case():
    base = engine.load_graph(engine.TBOX, engine.KNOWLEDGE, engine.CASES)
    changed = engine.reason(base, disabled=frozenset({"72-triage-age"}))
    levels = {str(e).split("#")[1]: str(t).split("#")[1] for e, t in changed.graph.subject_objects(GK.finalTriage)}
    assert {k for k in TRIAGE if levels[k] != TRIAGE[k]} == {"E006"}


def test_new_knowledge_changes_the_result_without_code_changes():
    data = engine.load_graph(engine.TBOX, engine.KNOWLEDGE, engine.CASES)
    data.parse(format="turtle", data="""
        @prefix gk:  <http://example.org/gastrokg/ontology#> .
        @prefix gkd: <http://example.org/gastrokg/data#> .
        gkd:Diclofenac a gk:Medication ; gk:drugClass gkd:NSAID .
        gkd:PT001 gk:takesMedication gkd:Diclofenac .
    """)
    graph = engine.reason(data).graph
    assert (GKD.PT001, RDF.type, GK.NSAIDUser) in graph
    assert (None, GK.concernsMedication, GKD.Diclofenac) in graph


# ---------------------------------------------------------------- data quality
def test_shipped_data_conforms():
    conforms, report = engine.shacl_report(engine.load_graph(engine.KNOWLEDGE, engine.CASES))
    assert conforms, report


BAD = {
    "expert CF above 1": "gkd:EL_P01_G01 gk:expertCF 1.5 .",
    "patient certainty above 1": "gkd:E001_obs_G01 gk:userCF 2.0 .",
    "medicine without class": "gkd:Mystery a gk:Medication .",
    "symptom both reported and denied": """gkd:E001 gk:hasObservation gkd:x .
        gkd:x a gk:SymptomObservation ; gk:deniedSymptom gkd:EpigastricPain ; gk:userCF 0.5 .""",
    "observation without symptom": "gkd:E001 gk:hasObservation gkd:y . gkd:y a gk:SymptomObservation ; gk:userCF 0.5 .",
    "rule with one condition": """gkd:R9 a gk:DiagnosticRule ; gk:code "R9" ; gk:concludes gkd:GERD ;
        gk:requiresSymptom gkd:Heartburn ; <http://purl.org/dc/terms/source> gkd:GroupAssignment .""",
}


@pytest.mark.parametrize("extra", BAD.values(), ids=BAD.keys())
def test_shapes_reject_bad_data(extra):
    data = engine.load_graph(engine.KNOWLEDGE, engine.CASES)
    if "gk:expertCF 1.5" in extra:
        data.remove((GKD.EL_P01_G01, GK.expertCF, None))
    if "gk:userCF 2.0" in extra:
        data.remove((GKD.E001_obs_G01, GK.userCF, None))
    data.parse(format="turtle", data="@prefix gk: <http://example.org/gastrokg/ontology#> .\n"
                                     "@prefix gkd: <http://example.org/gastrokg/data#> .\n" + extra)
    conforms, _ = engine.shacl_report(data)
    assert not conforms
