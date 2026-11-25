"""End-to-end browser tests, frontend security checks, and layout screenshots via Edge."""
from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
QA_ARTIFACTS = Path(os.environ.get("GASTROKG_QA_ARTIFACTS", str(ROOT / ".pytest_cache" / "qa-artifacts")))
FRONTEND_URL = "http://127.0.0.1:5500"
API_URL = "http://127.0.0.1:8000"


def _wait_ready(url: str, timeout: float = 25.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return
        except Exception:
            time.sleep(0.3)
    raise RuntimeError(f"Server did not become ready at {url}")


@pytest.fixture(scope="session")
def servers():
    api_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    fe_proc = subprocess.Popen(
        [sys.executable, str(ROOT / "scripts" / "serve_frontend.py"), "--host", "127.0.0.1", "--port", "5500"],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_ready(f"{API_URL}/api/health")
        _wait_ready(FRONTEND_URL)
        yield
    finally:
        fe_proc.terminate()
        api_proc.terminate()
        fe_proc.wait(timeout=5)
        api_proc.wait(timeout=5)


@pytest.fixture()
def guard_page(servers):
    from playwright.sync_api import sync_playwright

    QA_ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        errors: list[str] = []
        failed_requests: list[str] = []
        allow_failures = {"flag": False}

        page.on("pageerror", lambda err: errors.append(f"pageerror: {err}"))
        page.on(
            "console",
            lambda msg: None
            if (allow_failures["flag"] and ("ERR_FAILED" in msg.text or "Failed to load resource" in msg.text))
            else (errors.append(f"console.{msg.type}: {msg.text}") if msg.type == "error" else None),
        )
        page.on(
            "requestfailed",
            lambda req: None if allow_failures["flag"] else failed_requests.append(f"{req.method} {req.url}"),
        )
        page.add_init_script(
            "window.__cspViolations = []; window.addEventListener('securitypolicyviolation', e => window.__cspViolations.push(e.violatedDirective + ':' + e.blockedURI));"
        )

        yield page, allow_failures

        csp = page.evaluate("window.__cspViolations || []")
        browser.close()
        assert not csp, f"CSP violations detected: {csp}"
        assert not errors, f"Console/page errors detected: {errors}"
        assert not failed_requests, f"Failed requests detected: {failed_requests}"


def _assert_no_overflow(page):
    overflow = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
    assert not overflow, "Horizontal page overflow detected"


def test_uc1_sample_e001_and_manual_entry_agree(guard_page):
    page, _ = guard_page
    page.goto(f"{FRONTEND_URL}/#/result?case=E001")
    page.wait_for_selector("h1:has-text('Sample Case E001')")
    text = page.inner_text("main")
    assert "GERD" in text
    assert "0.987" in text
    for step_val in ("0.800", "0.896", "0.979", "0.987"):
        assert step_val in text

    # Manual entry for E001: age 34, G01=1.0, G02=0.8, G04=1.0, G07=0.6
    page.goto(f"{FRONTEND_URL}/#/consult")
    page.wait_for_selector("#age-input")
    page.fill("#age-input", "34")
    for sid, val in [("EpigastricPain", "1.0"), ("Nausea", "0.8"), ("Heartburn", "1.0"), ("SourTaste", "0.6")]:
        row = page.locator(f'[data-symptom-id="{sid}"]')
        row.get_by_role("button", name="Yes").click()
        row.locator('input[type="range"]').fill(val)
    page.get_by_role("button", name="Diagnose").click()
    page.wait_for_selector("h1:has-text('Screening Result')", timeout=45000)
    live_text = page.inner_text("main")
    assert "GERD" in live_text
    assert "0.987" in live_text
    for step_val in ("0.800", "0.896", "0.979", "0.987"):
        assert step_val in live_text

    # S11: zero storage in browser
    storage = page.evaluate(
        "({cookie: document.cookie, ls: Object.keys(localStorage).length, ss: Object.keys(sessionStorage).length})"
    )
    assert storage == {"cookie": "", "ls": 0, "ss": 0}


def test_uc2_triage_levels(guard_page):
    page, _ = guard_page
    page.goto(f"{FRONTEND_URL}/#/result?case=E004")
    page.wait_for_selector(".triage-banner-emergency")
    assert "SEEK EMERGENCY CARE NOW" in page.inner_text(".triage-banner-emergency")
    page.get_by_role("tab", name="Advice").click()
    assert "No follow-up question" in page.inner_text("main")

    page.goto(f"{FRONTEND_URL}/#/result?case=E005")
    page.wait_for_selector(".triage-Urgent")

    page.goto(f"{FRONTEND_URL}/#/result?case=E006")
    page.wait_for_selector(".triage-Referral")


def test_uc3_medication_alerts(guard_page):
    page, _ = guard_page
    for cid, expected in [("E007", "(3)"), ("E008", "(1)"), ("E009", "(1)")]:
        page.goto(f"{FRONTEND_URL}/#/result?case={cid}")
        page.wait_for_selector('[role="tab"]:has-text("Medication")')
        med_tab = page.get_by_role("tab", name=f"Medication {expected}")
        med_tab.click()
        if cid == "E007":
            txt = page.inner_text("main")
            assert "Ibuprofen" in txt
            assert "Paracetamol" in txt


def test_uc4_next_question_reruns(guard_page):
    page, _ = guard_page
    page.goto(f"{FRONTEND_URL}/#/result?case=E001")
    page.wait_for_selector("button:has-text('Run live')")
    page.get_by_role("button", name="Run live").click()
    page.wait_for_selector("span.badge:has-text('Live result')", timeout=45000)

    page.get_by_role("tab", name="Advice").click()
    assert "G08" in page.inner_text("main")
    page.get_by_role("button", name="Submit answer and run again").click()
    page.wait_for_selector("span.badge:has-text('Live result')", timeout=45000)
    page.get_by_role("tab", name="Diagnosis").click()
    assert "G08" in page.inner_text("main")


def test_uc5_uc6_rules_and_custom_knowledge(guard_page):
    page, _ = guard_page
    # Load E006 first, then disable 72-triage-age on #/rules
    page.goto(f"{FRONTEND_URL}/#/result?case=E006")
    page.wait_for_selector(".triage-Referral")
    page.goto(f"{FRONTEND_URL}/#/rules")
    page.wait_for_selector("button:has-text('72-triage-age')")
    page.get_by_role("button", name="72-triage-age").click()
    page.get_by_label("Enabled").uncheck()
    page.get_by_role("button", name="Run again").click()
    page.wait_for_selector("text=Comparison after re-run", timeout=45000)
    assert "Referral → PrimaryCare" in page.inner_text("main")

    # Re-enable rule and test Diclofenac preset on E001
    page.get_by_label("Enabled").check()
    page.goto(f"{FRONTEND_URL}/#/result?case=E001")
    page.wait_for_selector("h1:has-text('Sample Case E001')")
    page.goto(f"{FRONTEND_URL}/#/rules")
    page.wait_for_selector("button:has-text('Diclofenac')")
    page.get_by_role("button", name="Use preset: Add medication: Diclofenac (NSAID)").click()
    page.get_by_role("button", name="Run again").click()
    page.wait_for_selector("text=Comparison after re-run", timeout=45000)
    page.get_by_role("button", name="Open updated result").click()
    page.wait_for_selector("text=Custom knowledge is active")
    page.get_by_role("tab", name="Medication (3)").click()
    assert "Diclofenac" in page.inner_text("main")

    # R8 rule preset with Heartburn + CoughHoarseness
    page.goto(f"{FRONTEND_URL}/#/consult")
    page.wait_for_selector("#age-input")
    page.get_by_role("button", name="Clear answers").click()
    page.fill("#age-input", "35")
    page.locator('[data-symptom-id="Heartburn"]').get_by_role("button", name="Yes").click()
    page.locator('[data-symptom-id="CoughHoarseness"]').get_by_role("button", name="Yes").click()
    page.goto(f"{FRONTEND_URL}/#/rules")
    page.wait_for_selector("button:has-text('Add diagnostic rule: R8')")
    page.get_by_role("button", name="Use preset: Add diagnostic rule: R8 (Heartburn + Cough -> GERD)").click()
    page.get_by_role("button", name="Run again").click()
    page.wait_for_selector("text=Comparison after re-run", timeout=45000)
    page.get_by_role("button", name="Open updated result").click()
    page.wait_for_selector("text=Custom knowledge is active")
    assert "R8" in page.inner_text("main")

    # S07 XSS payload in custom medication label renders as text and logs no XSS-FIRED
    xss_events: list[str] = []
    page.on("console", lambda m: xss_events.append(m.text) if "XSS-FIRED" in m.text else None)
    page.goto(f"{FRONTEND_URL}/#/result?case=E001")
    page.wait_for_selector("h1:has-text('Sample Case E001')")
    page.goto(f"{FRONTEND_URL}/#/rules")
    page.wait_for_selector("#custom-turtle")
    page.get_by_role("button", name="Use preset: Add medication: Diclofenac (NSAID)").click()
    xss_turtle = (
        '@prefix gk: <http://example.org/gastrokg/ontology#> .\n'
        '@prefix gkd: <http://example.org/gastrokg/data#> .\n'
        '@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n'
        'gkd:Diclofenac a gk:Medication ; rdfs:label "<img src=x onerror=console.log(\'XSS-FIRED\')>"@en ; gk:drugClass gkd:NSAID .'
    )
    page.fill("#custom-turtle", xss_turtle)
    page.get_by_role("button", name="Run again").click()
    page.wait_for_selector("text=Comparison after re-run", timeout=45000)
    page.get_by_role("button", name="Open updated result").click()
    page.get_by_role("tab", name="Medication").click()
    assert "<img src=x onerror=console.log('XSS-FIRED')>" in page.inner_text("main")
    assert not xss_events


def test_negative_and_keyboard_states(guard_page):
    page, allow_failures = guard_page
    # N1: API stopped -> sample cases still open, live consult shows retry error
    allow_failures["flag"] = True
    page.route(f"{API_URL}/**", lambda route: route.abort())
    page.goto(f"{FRONTEND_URL}/#/result?case=E001")
    page.wait_for_selector("h1:has-text('Sample Case E001')")
    assert "0.987" in page.inner_text("main")

    page.goto(f"{FRONTEND_URL}/#/consult")
    page.wait_for_selector("text=Try again")
    page.unroute(f"{API_URL}/**")
    allow_failures["flag"] = False

    # N3: Reload on #/result without case and unknown route
    page.goto(f"{FRONTEND_URL}/#/result", wait_until="networkidle")
    page.reload(wait_until="networkidle")
    page.wait_for_selector("h1:has-text('No Screening Result Loaded')")
    page.goto(f"{FRONTEND_URL}/#/unknown-route-xyz")
    page.wait_for_selector("h1:has-text('Page not found')")

    # N2: 422, 429, 500, and slow (>5s) response + N4 double-click sends 1 request
    allow_failures["flag"] = True
    page.goto(f"{FRONTEND_URL}/#/consult")
    page.wait_for_selector("#age-input")
    page.fill("#age-input", "200")
    page.locator('[data-symptom-id="EpigastricPain"]').get_by_role("button", name="Yes").click()
    page.get_by_role("button", name="Diagnose").click()
    page.wait_for_selector(".field-error")
    assert page.input_value("#age-input") == "200"

    page.fill("#age-input", "35")
    page.route(f"{API_URL}/api/consultations", lambda route: route.fulfill(status=429, body="{}"))
    page.get_by_role("button", name="Diagnose").click()
    page.wait_for_selector("text=Too many requests, wait a minute")
    page.unroute(f"{API_URL}/api/consultations")

    page.route(
        f"{API_URL}/api/consultations",
        lambda route: route.fulfill(
            status=500,
            headers={"Content-Type": "application/json"},
            body='{"errors":[{"code":"internal","message":"fail"}],"requestId":"req-test-500"}',
        ),
    )
    page.get_by_role("button", name="Diagnose").click()
    page.wait_for_selector("text=req-test-500")
    page.unroute(f"{API_URL}/api/consultations")
    allow_failures["flag"] = False

    # Slow > 5s and double-click check (N4)
    hits = []

    def slow_handler(route):
        hits.append(1)
        time.sleep(5.4)
        route.continue_()

    page.route(f"{API_URL}/api/consultations", slow_handler)
    btn = page.get_by_role("button", name="Diagnose")
    btn.dblclick()
    page.wait_for_selector("text=waking up", timeout=15000)
    page.wait_for_selector("h1:has-text('Screening Result')", timeout=45000)
    page.unroute(f"{API_URL}/api/consultations")
    assert len(hits) == 1

    # K1: Keyboard-only navigation from Consultation to Result (reload to clear form)
    page.goto(f"{FRONTEND_URL}/#/consult", wait_until="networkidle")
    page.reload(wait_until="networkidle")
    page.wait_for_selector("#age-input")
    page.focus("#age-input")
    page.keyboard.type("30")
    page.focus('[data-symptom-id="EpigastricPain"] button:has-text("Yes")')
    page.keyboard.press("Enter")
    page.focus('button[type="submit"]')
    page.keyboard.press("Enter")
    page.wait_for_selector("h1:has-text('Screening Result')", timeout=45000)


def test_visual_qc_and_graph_interactions(guard_page):
    page, _ = guard_page
    # Graph interactions with real mouse on E007
    page.goto(f"{FRONTEND_URL}/#/result?case=E007")
    page.wait_for_selector("h1")
    page.get_by_role("tab", name="Graph").click()
    page.wait_for_selector(".graph-svg .node")
    initial_nodes = page.locator(".graph-svg .node").count()
    assert initial_nodes >= 2

    # Click a node, expand, collapse, hide, double-click, drag node, reset, fit, origin toggles
    first_node = page.locator(".graph-svg .node").first
    first_node.scroll_into_view_if_needed()
    box = first_node.bounding_box()
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.wait_for_selector(".graph-panel:not([hidden])")
    expand_btn = page.locator(".graph-panel button:has-text('+ Expand')")
    if expand_btn.is_enabled():
        expand_btn.click()
        assert page.locator(".graph-svg .node").count() >= initial_nodes
    collapse_btn = page.locator(".graph-panel button:has-text('− Collapse')")
    if collapse_btn.is_enabled():
        collapse_btn.click()
    # Double-click node to expand
    box2 = first_node.bounding_box()
    page.mouse.dblclick(box2["x"] + box2["width"] / 2, box2["y"] + box2["height"] / 2)
    # Drag node
    box3 = first_node.bounding_box()
    page.mouse.move(box3["x"] + box3["width"] / 2, box3["y"] + box3["height"] / 2)
    page.mouse.down()
    page.mouse.move(box3["x"] + box3["width"] / 2 + 25, box3["y"] + box3["height"] / 2 + 20)
    page.mouse.up()
    # Hide a non-focus node
    last_node = page.locator(".graph-svg .node").last
    last_box = last_node.bounding_box()
    page.mouse.click(last_box["x"] + last_box["width"] / 2, last_box["y"] + last_box["height"] / 2)
    page.locator(".graph-panel button:has-text('× Hide')").click()
    page.get_by_role("button", name="Fit view").click()
    page.get_by_role("button", name="Reset").click()
    for origin in ("Asserted", "RDFS", "OWL", "Rule"):
        btn = page.locator(f'.graph-key:has-text("{origin}")')
        btn.click()
        assert btn.get_attribute("aria-pressed") == "false"
        btn.click()
        assert btn.get_attribute("aria-pressed") == "true"

    # Mouse drag and wheel zoom on SVG canvas
    svg_box = page.locator(".graph-svg").bounding_box()
    cx, cy = svg_box["x"] + svg_box["width"] / 2, svg_box["y"] + svg_box["height"] / 2
    page.mouse.move(cx, cy)
    page.mouse.down()
    page.mouse.move(cx + 40, cy + 30)
    page.mouse.up()
    page.mouse.wheel(0, -120)

    # Multi-viewport Visual QC screenshots + layout checks
    routes = [
        ("home", f"{FRONTEND_URL}/#/"),
        ("consult", f"{FRONTEND_URL}/#/consult"),
        ("result-e004", f"{FRONTEND_URL}/#/result?case=E004"),
        ("result-e007", f"{FRONTEND_URL}/#/result?case=E007"),
        ("rules", f"{FRONTEND_URL}/#/rules"),
        ("queries", f"{FRONTEND_URL}/#/queries"),
        ("about", f"{FRONTEND_URL}/#/about"),
    ]
    for width, height in [(360, 800), (768, 1024), (1440, 900)]:
        page.set_viewport_size({"width": width, "height": height})
        for name, url in routes:
            page.goto(url)
            page.wait_for_selector("h1")
            if name == "consult":
                page.wait_for_selector("#age-input")
            if name == "queries":
                page.wait_for_selector("article.card")
            _assert_no_overflow(page)
            if width == 360:
                small_targets = page.evaluate("""() => {
                    return [...document.querySelectorAll('button, a.btn, input[type="number"], input[type="search"]')]
                        .filter(el => el.offsetParent !== null)
                        .map(el => ({text: (el.textContent || el.id).trim().slice(0, 30), h: el.getBoundingClientRect().height}))
                        .filter(x => x.h > 0 && x.h < 43.5);
                }""")
                assert not small_targets, f"Touch targets < 44px on {name} at 360px: {small_targets}"
            page.screenshot(path=str(QA_ARTIFACTS / f"{name}-{width}x{height}.png"), full_page=True)

        # Also capture Graph and Reasoning tabs at each viewport
        page.goto(f"{FRONTEND_URL}/#/result?case=E007")
        page.wait_for_selector("h1")
        page.get_by_role("tab", name="Graph").click()
        page.wait_for_selector(".graph-svg .node")
        _assert_no_overflow(page)
        page.screenshot(path=str(QA_ARTIFACTS / f"tab-graph-{width}x{height}.png"), full_page=True)

        page.get_by_role("tab", name="Reasoning").click()
        page.wait_for_selector("text=Triple counts")
        _assert_no_overflow(page)
        page.screenshot(path=str(QA_ARTIFACTS / f"tab-reasoning-{width}x{height}.png"), full_page=True)
