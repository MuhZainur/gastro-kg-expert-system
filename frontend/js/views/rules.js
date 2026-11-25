import { html, useEffect, useState } from "../../vendor/htm-preact-standalone.module.js";
import { getPresets, getRules, runConsultation } from "../api.js";
import { ErrorPanel } from "../components/error_panel.js";
import { LoadingPanel } from "../components/loading_panel.js";
import { formatCf } from "../format.js";
import { appState, buildConsultationPayload } from "../store.js";

export function RulesView({ onNavigate }) {
  const [rules, setRules] = useState(appState.rulesList || []);
  const [presets, setPresets] = useState([]);
  const [selectedRule, setSelectedRule] = useState(null);
  const [loading, setLoading] = useState(!appState.rulesList);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [, setTick] = useState(0);

  const refresh = () => setTick((n) => n + 1);

  const loadAll = () => {
    setLoading(true);
    setError(null);
    Promise.all([
      appState.rulesList ? Promise.resolve({ rules: appState.rulesList }) : getRules(),
      getPresets().catch(() => []),
    ])
      .then(([rulesRes, presetsRes]) => {
        appState.rulesList = rulesRes.rules;
        setRules(rulesRes.rules);
        setPresets(presetsRes);
        if (!selectedRule && rulesRes.rules.length) {
          setSelectedRule(rulesRes.rules[0].name);
        }
        setLoading(false);
      })
      .catch((err) => {
        setError(err);
        setLoading(false);
      });
  };

  useEffect(() => {
    loadAll();
  }, []);

  const toggleRule = (name) => {
    const list = appState.form.disabledRules;
    const idx = list.indexOf(name);
    if (idx >= 0) list.splice(idx, 1);
    else list.push(name);
    refresh();
  };

  const applyPreset = (preset) => {
    appState.form.extraKnowledge = preset.turtle;
    if (preset.addsMedication) {
      appState.form.customMedications = [preset.addsMedication];
      appState.form.medications[preset.addsMedication.id] = { selected: true, regular: true };
    }
    refresh();
  };

  const clearCustomKnowledge = () => {
    appState.form.extraKnowledge = null;
    for (const cm of appState.form.customMedications || []) {
      delete appState.form.medications[cm.id];
    }
    appState.form.customMedications = [];
    refresh();
  };

  const runAgain = async () => {
    if (running) return;
    const formPayload = buildConsultationPayload();
    const baseReq = formPayload.symptoms.length > 0 ? formPayload : appState.lastRequest;
    if (!baseReq || !baseReq.symptoms || baseReq.symptoms.length === 0) {
      setError({ status: 422, message: "No consultation answers loaded yet. Enter symptoms on Consultation or open a sample case first.", errors: [] });
      return;
    }
    const payload = {
      ...baseReq,
      disabledRules: [...appState.form.disabledRules],
      extraKnowledge: appState.form.extraKnowledge && appState.form.extraKnowledge.trim() ? appState.form.extraKnowledge : null,
    };

    appState.previousResult = null;
    setRunning(true);
    setError(null);
    try {
      const prev = appState.result;
      const next = await runConsultation(payload);
      appState.previousResult = prev;
      appState.lastRequest = payload;
      appState.result = next;
      appState.resultSource = "live";
      appState.sampleId = null;
      appState.sampleTitle = null;
      setRunning(false);
      refresh();
    } catch (err) {
      setError(err);
      setRunning(false);
    }
  };

  const groups = [...new Set(rules.map((r) => r.group))];
  const active = rules.find((r) => r.name === selectedRule) || rules[0];
  const prev = appState.previousResult;
  const curr = appState.result;

  return html`
    <div>
      <h1 tabindex="-1">SPARQL Rules & Custom Knowledge</h1>
      <p class="small muted">
        Inspect the 30 SPARQL CONSTRUCT rules, toggle rules to test sensitivity, or add validated Turtle knowledge.
      </p>

      ${loading ? html`<${LoadingPanel} label="Loading rules..." />` : null}
      ${error ? html`<${ErrorPanel} error=${error} onRetry=${loadAll} />` : null}

      ${prev && curr
        ? html`
            <div class="notice" role="status">
              <strong>Comparison after re-run:</strong>
              <div>
                Triage: <code>${prev.triage ? prev.triage.level : "none"}</code> → <code>${curr.triage ? curr.triage.level : "none"}</code>
                · Top hypothesis: ${prev.hypotheses[0]?.disease.label || "none"} (${prev.hypotheses[0] ? formatCf(prev.hypotheses[0].cf) : "-"})
                → ${curr.hypotheses[0]?.disease.label || "none"} (${curr.hypotheses[0] ? formatCf(curr.hypotheses[0].cf) : "-"})
              </div>
              <div class="row-actions">
                <button type="button" class="btn btn-sm" onClick=${() => onNavigate("#/result")}>
                  Open updated result
                </button>
              </div>
            </div>
          `
        : null}

      ${rules.length > 0
        ? html`
            <div class="split-layout">
              <div class="card">
                <h2>30 Rules (${appState.form.disabledRules.length} disabled)</h2>
                ${groups.map((grp) => html`
                  <div key=${grp}>
                    <h3>${grp}</h3>
                    ${rules.filter((r) => r.group === grp).map((r) => {
                      const disabled = appState.form.disabledRules.includes(r.name);
                      return html`
                        <div class="row-actions" key=${r.name}>
                          <button
                            type="button"
                            class=${`rule-list-btn ${active?.name === r.name ? "active" : ""}`}
                            onClick=${() => setSelectedRule(r.name)}
                          >
                            <span>${r.name}</span>
                            <span class="small muted">${disabled ? "OFF" : "ON"}</span>
                          </button>
                        </div>
                      `;
                    })}
                  </div>
                `)}
              </div>

              <div>
                ${active
                  ? html`
                      <section class="card">
                        <div class="hyp-head">
                          <h2>${active.name}: ${active.title}</h2>
                          <label class="check-label">
                            <input
                              type="checkbox"
                              checked=${!appState.form.disabledRules.includes(active.name)}
                              onChange=${() => toggleRule(active.name)}
                            />
                            <span>Enabled</span>
                          </label>
                        </div>
                        <p class="muted">${active.description}</p>
                        <p class="small">Group: <strong>${active.group}</strong> · Iterative: ${active.iterate ? "Yes" : "No"}</p>
                        <pre>${active.query}</pre>
                      </section>
                    `
                  : null}

                <section class="card">
                  <h2>Custom Knowledge (Turtle allow-list)</h2>
                  <p class="small muted">
                    Add new <code>gk:Medication</code> or <code>gk:DiagnosticRule</code> triples (max 4 KB, 40 triples, validated by SHACL).
                  </p>
                  <div class="row-actions">
                    ${presets.map((p) => html`
                      <button type="button" class="btn btn-sm" key=${p.id} onClick=${() => applyPreset(p)}>
                        Use preset: ${p.title}
                      </button>
                    `)}
                    <button type="button" class="btn btn-sm" onClick=${clearCustomKnowledge}>
                      Clear custom knowledge
                    </button>
                  </div>
                  <div class="field-group">
                    <label class="field-label" for="custom-turtle">Turtle snippet</label>
                    <textarea
                      id="custom-turtle"
                      rows="8"
                      value=${appState.form.extraKnowledge || ""}
                      onInput=${(e) => {
                        appState.form.extraKnowledge = e.target.value;
                        refresh();
                      }}
                    ></textarea>
                  </div>
                  ${running ? html`<${LoadingPanel} label="Re-running consultation with updated rules..." />` : null}
                  <div class="row-actions">
                    <button type="button" class="btn btn-primary" disabled=${running} onClick=${runAgain}>
                      ${running ? "Running..." : "Run again"}
                    </button>
                  </div>
                </section>
              </div>
            </div>
          `
        : null}
    </div>
  `;
}
