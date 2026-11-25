import { html, useEffect, useState } from "../../vendor/htm-preact-standalone.module.js";
import { getForm, runConsultation } from "../api.js";
import { ErrorPanel } from "../components/error_panel.js";
import { LoadingPanel } from "../components/loading_panel.js";
import { SymptomRow } from "../components/symptom_row.js";
import { appState, buildConsultationPayload, resetForm } from "../store.js";

export function ConsultView({ onNavigate }) {
  const [schema, setSchema] = useState(appState.formSchema);
  const [loadingForm, setLoadingForm] = useState(!appState.formSchema);
  const [formError, setFormError] = useState(null);
  const [search, setSearch] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [, setTick] = useState(0);

  const forceUpdate = () => setTick((n) => n + 1);

  const loadSchema = () => {
    setLoadingForm(true);
    setFormError(null);
    getForm()
      .then((data) => {
        appState.formSchema = data;
        setSchema(data);
        setLoadingForm(false);
      })
      .catch((err) => {
        setFormError(err);
        setLoadingForm(false);
      });
  };

  useEffect(() => {
    if (!schema) loadSchema();
  }, []);

  const fieldErrorFor = (prefix) => {
    if (!submitError || submitError.status !== 422 || !submitError.errors) return null;
    const hit = submitError.errors.find((e) => e.field === prefix || (e.field && e.field.startsWith(prefix + ".")));
    return hit ? hit.message : null;
  };

  const handleSymptomChange = (id, nextVal) => {
    if (nextVal.answer === "skip") {
      delete appState.form.symptoms[id];
    } else {
      appState.form.symptoms[id] = nextVal;
    }
    forceUpdate();
  };

  const toggleRisk = (id) => {
    const list = appState.form.riskFactors;
    const idx = list.indexOf(id);
    if (idx >= 0) list.splice(idx, 1);
    else list.push(id);
    forceUpdate();
  };

  const toggleMed = (id) => {
    const current = appState.form.medications[id];
    if (current?.selected) {
      delete appState.form.medications[id];
    } else {
      appState.form.medications[id] = { selected: true, regular: false };
    }
    forceUpdate();
  };

  const toggleMedRegular = (id) => {
    const current = appState.form.medications[id];
    if (current) {
      current.regular = !current.regular;
      forceUpdate();
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setSubmitError(null);
    const payload = buildConsultationPayload();
    try {
      const result = await runConsultation(payload);
      appState.lastRequest = payload;
      appState.previousResult = null;
      appState.result = result;
      appState.resultSource = "live";
      appState.sampleId = null;
      appState.sampleTitle = null;
      setSubmitting(false);
      onNavigate("#/result");
    } catch (err) {
      setSubmitError(err);
      setSubmitting(false);
    }
  };

  const query = search.trim().toLowerCase();
  const matchesSearch = (sym) => {
    if (!query) return true;
    const haystack = [sym.code, sym.label, sym.labelId, ...(sym.altLabels || [])]
      .join(" ")
      .toLowerCase();
    return haystack.includes(query);
  };

  const answeredCount = Object.values(appState.form.symptoms).filter(
    (s) => s.answer === "yes" || s.answer === "no"
  ).length;

  const totalSymptoms = schema
    ? schema.symptomGroups.reduce((sum, g) => sum + g.symptoms.length, 0)
    : 22;

  const allMedications = schema
    ? [
        ...schema.medications,
        ...(appState.form.customMedications || []).filter(
          (cm) => !schema.medications.some((m) => m.id === cm.id)
        ).map((cm) => ({ id: cm.id, label: cm.label, drugClass: { id: "Custom", label: "Custom" } })),
      ]
    : [];

  return html`
    <div>
      <h1 tabindex="-1">Patient Screening Consultation</h1>
      <p class="small muted">
        Answer the symptoms you know (Yes or No) and skip the rest. Warning signs appear first.
      </p>

      ${loadingForm ? html`<${LoadingPanel} label="Loading consultation form..." />` : null}
      ${formError ? html`<${ErrorPanel} error=${formError} onRetry=${loadSchema} />` : null}

      ${schema
        ? html`
            <form onSubmit=${handleSubmit} noValidate>
              ${appState.form.extraKnowledge
                ? html`
                    <div class="notice notice-warn">
                      <strong>Custom knowledge is active.</strong>
                      <span> Added Turtle rules or medications will be included in this consultation.</span>
                    </div>
                  `
                : null}

              <section class="card">
                <h2>1. Patient age</h2>
                <div class="field-group">
                  <label class="field-label" for="age-input">Age in years (0 to 120)</label>
                  <input
                    id="age-input"
                    class="age-input"
                    type="number"
                    min="0"
                    max="120"
                    step="1"
                    value=${appState.form.age}
                    onInput=${(e) => {
                      appState.form.age = e.target.value;
                      forceUpdate();
                    }}
                  />
                  ${fieldErrorFor("age") ? html`<div class="field-error">${fieldErrorFor("age")}</div>` : null}
                </div>
              </section>

              <section class="card">
                <div class="hyp-head">
                  <h2>2. Symptoms (${answeredCount} of ${totalSymptoms} answered)</h2>
                  <button
                    type="button"
                    class="btn btn-sm"
                    onClick=${() => {
                      resetForm();
                      setSubmitError(null);
                      forceUpdate();
                    }}
                  >
                    Clear answers
                  </button>
                </div>

                <div class="field-group">
                  <label class="field-label" for="symptom-search">Filter symptoms (English, Indonesian, or lay terms)</label>
                  <input
                    id="symptom-search"
                    type="search"
                    placeholder="e.g. heartburn, ulu hati perih, muntah darah"
                    value=${search}
                    onInput=${(e) => setSearch(e.target.value)}
                  />
                </div>

                ${fieldErrorFor("symptoms") ? html`<div class="field-error">${fieldErrorFor("symptoms")}</div>` : null}

                ${schema.symptomGroups.map((group) => {
                  const visible = group.symptoms.filter(matchesSearch);
                  if (visible.length === 0) return null;
                  return html`
                    <div key=${group.id}>
                      <h3>${group.title}</h3>
                      ${visible.map((sym) => html`
                        <${SymptomRow}
                          key=${sym.id}
                          symptom=${sym}
                          value=${appState.form.symptoms[sym.id]}
                          onChange=${handleSymptomChange}
                        />
                      `)}
                    </div>
                  `;
                })}
              </section>

              <section class="card">
                <h2>3. Risk factors</h2>
                <div class="check-grid">
                  ${schema.riskFactors.map((rf) => {
                    const checked = appState.form.riskFactors.includes(rf.id);
                    return html`
                      <div class="check-item" key=${rf.id}>
                        <label class="check-label">
                          <input
                            type="checkbox"
                            checked=${checked}
                            onChange=${() => toggleRisk(rf.id)}
                          />
                          <span>
                            <strong>${rf.label}</strong>
                            <span class="symptom-id-label">${rf.labelId}</span>
                          </span>
                        </label>
                      </div>
                    `;
                  })}
                </div>
              </section>

              <section class="card">
                <h2>4. Current medications</h2>
                <div class="check-grid">
                  ${allMedications.map((med) => {
                    const state = appState.form.medications[med.id];
                    const selected = Boolean(state?.selected);
                    return html`
                      <div class="check-item" key=${med.id}>
                        <label class="check-label">
                          <input
                            type="checkbox"
                            checked=${selected}
                            onChange=${() => toggleMed(med.id)}
                          />
                          <span>
                            <strong>${med.label}</strong>
                            <span class="symptom-id-label">${med.drugClass.label}</span>
                          </span>
                        </label>
                        ${selected
                          ? html`
                              <label class="check-label small">
                                <input
                                  type="checkbox"
                                  checked=${Boolean(state?.regular)}
                                  onChange=${() => toggleMedRegular(med.id)}
                                />
                                <span>Taken regularly</span>
                              </label>
                            `
                          : null}
                      </div>
                    `;
                  })}
                </div>
              </section>

              ${submitting ? html`<${LoadingPanel} label="Validating SHACL shapes and running OWL 2 RL + 30 SPARQL rules..." />` : null}
              ${submitError ? html`<${ErrorPanel} error=${submitError} onRetry=${() => handleSubmit({ preventDefault: () => {} })} />` : null}

              <div class="row-actions">
                <button type="submit" class="btn btn-primary" disabled=${submitting}>
                  ${submitting ? "Diagnosing..." : "Diagnose"}
                </button>
                <span class="small muted">${answeredCount} symptom(s) answered</span>
              </div>
            </form>
          `
        : null}
    </div>
  `;
}
