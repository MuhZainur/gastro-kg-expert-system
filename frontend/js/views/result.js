import { html, useEffect, useState } from "../../vendor/htm-preact-standalone.module.js";
import { getSampleCase, runConsultation } from "../api.js";
import { ErrorPanel } from "../components/error_panel.js";
import { LoadingPanel } from "../components/loading_panel.js";
import { TriageBanner } from "../components/triage_banner.js";
import { AdviceTab } from "../tabs/advice.js";
import { DiagnosisTab } from "../tabs/diagnosis.js";
import { MedicationTab } from "../tabs/medication.js";
import { appState, loadRequestIntoForm } from "../store.js";

const TABS = [
  { id: "diagnosis", label: "Diagnosis" },
  { id: "medication", label: "Medication" },
  { id: "advice", label: "Advice" },
  { id: "graph", label: "Graph" },
  { id: "reasoning", label: "Reasoning" },
];

export function ResultView({ caseParam, onNavigate }) {
  const [activeTab, setActiveTab] = useState("diagnosis");
  const [loading, setLoading] = useState(Boolean(caseParam && appState.sampleId !== caseParam));
  const [error, setError] = useState(null);
  const [graphMod, setGraphMod] = useState(null);
  const [reasoningMod, setReasoningMod] = useState(null);
  const [, setTick] = useState(0);

  const refresh = () => setTick((n) => n + 1);

  useEffect(() => {
    if (!caseParam) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    getSampleCase(caseParam)
      .then((data) => {
        if (cancelled) return;
        loadRequestIntoForm(data.request);
        appState.lastRequest = data.request;
        appState.result = data.result;
        appState.resultSource = "sample";
        appState.sampleId = data.id;
        appState.sampleTitle = data.title;
        setLoading(false);
        refresh();
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err);
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [caseParam]);

  useEffect(() => {
    if (activeTab === "graph" && !graphMod) {
      import("../tabs/graph.js").then(setGraphMod).catch(() => {});
    }
    if (activeTab === "reasoning" && !reasoningMod) {
      import("../tabs/reasoning.js").then(setReasoningMod).catch(() => {});
    }
  }, [activeTab]);

  const handleRunLive = async () => {
    if (!appState.lastRequest || loading) return;
    setLoading(true);
    setError(null);
    try {
      const liveResult = await runConsultation(appState.lastRequest);
      appState.result = liveResult;
      appState.resultSource = "live";
      appState.sampleId = null;
      appState.sampleTitle = null;
      setLoading(false);
      refresh();
    } catch (err) {
      setError(err);
      setLoading(false);
    }
  };

  const handleAnswerQuestion = async (symptomId, answer, certainty) => {
    if (loading) return;
    appState.form.symptoms[symptomId] = { answer, certainty };
    const baseReq = appState.lastRequest || {
      age: Number(appState.form.age),
      riskFactors: [...appState.form.riskFactors],
      medications: [],
      symptoms: [],
      disabledRules: [...appState.form.disabledRules],
      extraKnowledge: appState.form.extraKnowledge,
    };
    const nextSymptoms = (baseReq.symptoms || []).filter((s) => s.id !== symptomId);
    nextSymptoms.push({ id: symptomId, answer, certainty: Number(certainty.toFixed(1)) });
    const nextPayload = { ...baseReq, symptoms: nextSymptoms };

    setLoading(true);
    setError(null);
    try {
      const liveResult = await runConsultation(nextPayload);
      loadRequestIntoForm(nextPayload);
      appState.lastRequest = nextPayload;
      appState.result = liveResult;
      appState.resultSource = "live";
      appState.sampleId = null;
      appState.sampleTitle = null;
      setLoading(false);
      refresh();
    } catch (err) {
      setError(err);
      setLoading(false);
    }
  };

  const onTabKeyDown = (e, idx) => {
    if (e.key === "ArrowRight") {
      e.preventDefault();
      setActiveTab(TABS[(idx + 1) % TABS.length].id);
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      setActiveTab(TABS[(idx - 1 + TABS.length) % TABS.length].id);
    }
  };

  const result = appState.result;

  if (loading && !result) {
    return html`
      <div>
        <h1 tabindex="-1">Screening Result</h1>
        <${LoadingPanel} label="Loading screening result..." />
      </div>
    `;
  }

  if (!result) {
    return html`
      <div>
        <h1 tabindex="-1">No Screening Result Loaded</h1>
        ${error ? html`<${ErrorPanel} error=${error} />` : null}
        <div class="card">
          <p>Start a new consultation or choose one of the 13 synthetic sample cases from the home page.</p>
          <div class="row-actions">
            <a class="btn btn-primary" href="#/consult">Start consultation</a>
            <a class="btn" href="#/">Back to home</a>
          </div>
        </div>
      </div>
    `;
  }

  return html`
    <div>
      <div class="hyp-head">
        <div>
          <h1 tabindex="-1">
            ${appState.sampleId ? `Sample Case ${appState.sampleId}: ${appState.sampleTitle}` : "Screening Result"}
          </h1>
          <div class="row-actions small">
            ${result.meta.precomputed
              ? html`<span class="badge">Stored result</span>`
              : html`<span class="badge triage-SelfMonitor">Live result · ${result.meta.seconds?.total?.toFixed(2) ?? "?"}s</span>`}
            <button type="button" class="btn btn-sm" onClick=${() => onNavigate("#/consult")}>
              Edit answers
            </button>
            ${result.meta.precomputed
              ? html`
                  <button type="button" class="btn btn-sm" disabled=${loading} onClick=${handleRunLive}>
                    ${loading ? "Running..." : "Run live"}
                  </button>
                `
              : null}
          </div>
        </div>
      </div>

      ${loading ? html`<${LoadingPanel} label="Running live consultation..." />` : null}
      ${error ? html`<${ErrorPanel} error=${error} onRetry=${handleRunLive} />` : null}

      <div class="notice" role="note">
        <strong>Disclaimer:</strong> ${result.disclaimer}
      </div>

      <${TriageBanner} triage=${result.triage} meta=${result.meta} />

      <div class="tablist" role="tablist" aria-label="Result sections">
        ${TABS.map((tab, idx) => {
          const count =
            tab.id === "medication" && result.alerts.length > 0
              ? ` (${result.alerts.length})`
              : tab.id === "diagnosis"
              ? ` (${result.hypotheses.length})`
              : "";
          return html`
            <button
              key=${tab.id}
              type="button"
              role="tab"
              id=${`tab-${tab.id}`}
              aria-selected=${activeTab === tab.id ? "true" : "false"}
              aria-controls=${`panel-${tab.id}`}
              class="tab-btn"
              onClick=${() => setActiveTab(tab.id)}
              onKeyDown=${(e) => onTabKeyDown(e, idx)}
            >
              ${tab.label}${count}
            </button>
          `;
        })}
      </div>

      <div id=${`panel-${activeTab}`} role="tabpanel" aria-labelledby=${`tab-${activeTab}`}>
        ${activeTab === "diagnosis"
          ? html`<${DiagnosisTab} hypotheses=${result.hypotheses} ruleMatches=${result.ruleMatches} />`
          : activeTab === "medication"
          ? html`<${MedicationTab} alerts=${result.alerts} />`
          : activeTab === "advice"
          ? html`
              <${AdviceTab}
                recommendations=${result.recommendations}
                nextQuestion=${result.nextQuestion}
                triage=${result.triage}
                onAnswerQuestion=${handleAnswerQuestion}
                busy=${loading}
              />
            `
          : activeTab === "graph"
          ? graphMod
            ? html`<${graphMod.GraphTab} graph=${result.graph} />`
            : html`<${LoadingPanel} label="Loading graph explorer..." />`
          : reasoningMod
          ? html`<${reasoningMod.ReasoningTab} owlFacts=${result.owlFacts} meta=${result.meta} />`
          : html`<${LoadingPanel} label="Loading reasoning summary..." />`}
      </div>
    </div>
  `;
}
