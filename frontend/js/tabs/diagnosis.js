import { html, useState } from "../../vendor/htm-preact-standalone.module.js";
import { formatCf, isSafeHttpsUrl, statusText } from "../format.js";

function SourceList({ sources }) {
  if (!sources || sources.length === 0) return html`<span class="muted">None</span>`;
  return html`
    <span>
      ${sources.map((src, i) => html`
        <span key=${i}>
          ${i > 0 ? ", " : ""}
          ${isSafeHttpsUrl(src)
            ? html`<a href=${src} target="_blank" rel="noopener noreferrer">Source</a>`
            : html`<span>${src}</span>`}
        </span>
      `)}
    </span>
  `;
}

export function DiagnosisTab({ hypotheses, ruleMatches }) {
  const [expanded, setExpanded] = useState(() => new Set(hypotheses[0] ? [hypotheses[0].disease.id] : []));

  if (!hypotheses || hypotheses.length === 0) {
    return html`
      <div class="card">
        <p class="muted">No diagnostic hypotheses were generated for this consultation (rules may be disabled or no evidence links matched).</p>
      </div>
    `;
  }

  const toggle = (id) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return html`
    <div>
      <p class="small muted">
        A certainty factor (CF) is a belief score from -1.000 to 1.000, not a probability.
      </p>
      ${hypotheses.map((h) => {
        const isOpen = expanded.has(h.disease.id);
        const supportSteps = (h.steps || []).filter((s) => s.polarity !== "oppose");
        const opposeSteps = (h.steps || []).filter((s) => s.polarity === "oppose");
        const diseaseRules = (ruleMatches || []).filter((m) => m.disease.id === h.disease.id);

        return html`
          <article class="card" key=${h.disease.id}>
            <div class="hyp-head">
              <div>
                <h3>
                  #${h.rank} · ${h.disease.label} <span class="small muted">(${h.code})</span>
                </h3>
                <div class="row-actions">
                  <span class="badge">${statusText(h.status)}</span>
                  <span class="small muted">Rule coverage: ${Math.round(h.coverage * 100)}%</span>
                </div>
              </div>
              <div class="row-actions">
                <strong title=${`Exact CF: ${h.cf}`}>CF ${formatCf(h.cf)}</strong>
                <button
                  type="button"
                  class="btn btn-sm"
                  aria-expanded=${isOpen ? "true" : "false"}
                  onClick=${() => toggle(h.disease.id)}
                >
                  ${isOpen ? "Hide trace" : "Show trace"}
                </button>
              </div>
            </div>

            <progress
              class="cf-meter"
              max="1"
              value=${Math.max(0, Math.min(1, Number(h.cf) || 0))}
              aria-label=${`Certainty factor for ${h.disease.label}`}
            ></progress>

            ${isOpen
              ? html`
                  <div>
                    <h4>Supporting evidence trace</h4>
                    ${supportSteps.length > 0
                      ? html`
                          <div class="table-scroll">
                            <table class="stack-table">
                              <thead>
                                <tr>
                                  <th>Step</th>
                                  <th>Symptom</th>
                                  <th>Calculation (patient × expert = item)</th>
                                  <th>Before → After</th>
                                  <th>Source</th>
                                </tr>
                              </thead>
                              <tbody>
                                ${supportSteps.map((s) => html`
                                  <tr key=${s.seq}>
                                    <td data-label="Step">${s.seq}</td>
                                    <td data-label="Symptom">
                                      <div>
                                        <strong>${s.symptom.code}</strong> · ${s.symptom.label}
                                        <div class="small muted">${s.symptom.labelId}</div>
                                      </div>
                                    </td>
                                    <td data-label="Patient × expert">
                                      <div>${s.patientCertainty.toFixed(1)} × ${formatCf(s.expertWeight)} = <strong>${formatCf(s.itemCf)}</strong></div>
                                    </td>
                                    <td data-label="Before → After">
                                      <div>${formatCf(s.before)} → <strong>${formatCf(s.after)}</strong></div>
                                    </td>
                                    <td data-label="Source"><${SourceList} sources=${s.sources} /></td>
                                  </tr>
                                `)}
                              </tbody>
                            </table>
                          </div>
                        `
                      : html`<p class="small muted">No supporting symptom steps recorded.</p>`}

                    ${opposeSteps.length > 0
                      ? html`
                          <div class="notice notice-warn">
                            <h4>Opposing evidence</h4>
                            <p class="small">Combined opposition CF: <strong>${formatCf(h.opposition)}</strong> (combined support CF: ${formatCf(h.support)})</p>
                            <div class="table-scroll">
                              <table class="stack-table">
                                <thead>
                                  <tr>
                                    <th>Symptom</th>
                                    <th>Calculation</th>
                                    <th>Before → After</th>
                                    <th>Source</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  ${opposeSteps.map((s) => html`
                                    <tr key=${`opp-${s.seq}`}>
                                      <td data-label="Symptom">
                                        <div>${s.denied ? "Denied: " : ""}${s.symptom.code} · ${s.symptom.label}</div>
                                      </td>
                                      <td data-label="Calculation">
                                        <div>${s.patientCertainty.toFixed(1)} × ${formatCf(s.expertWeight)} = ${formatCf(s.itemCf)}</div>
                                      </td>
                                      <td data-label="Before → After"><div>${formatCf(s.before)} → ${formatCf(s.after)}</div></td>
                                      <td data-label="Source"><${SourceList} sources=${s.sources} /></td>
                                    </tr>
                                  `)}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        `
                      : null}

                    ${h.missing && h.missing.length > 0
                      ? html`
                          <p class="small">
                            <strong>Missing rule conditions:</strong>
                            ${h.missing.map((m) => ` ${m.code} ${m.label}`).join("; ")}
                          </p>
                        `
                      : null}

                    ${h.riskFactors && h.riskFactors.length > 0
                      ? html`
                          <p class="small">
                            <strong>Risk factors in context (do not alter CF):</strong>
                            ${h.riskFactors.map((rf) => ` ${rf.label} (${rf.labelId})`).join(", ")}
                          </p>
                        `
                      : null}

                    ${diseaseRules.length > 0
                      ? html`
                          <div class="small">
                            <strong>Evaluated diagnostic rules:</strong>
                            <ul>
                              ${diseaseRules.map((m) => html`
                                <li key=${m.rule}>
                                  <code>${m.rule}</code>: ${m.matched}/${m.required} conditions
                                  ${`${m.fired ? " (fired)" : " (not fired)"} — ${m.conditions.map((c) => `${c.code} ${c.met ? "✓" : "○"}`).join(", ")}`}
                                </li>
                              `)}
                            </ul>
                          </div>
                        `
                      : null}

                    <p class="small"><strong>Initial advice:</strong> ${h.advice}</p>
                  </div>
                `
              : null}
          </article>
        `;
      })}
    </div>
  `;
}
