import { html } from "../../vendor/htm-preact-standalone.module.js";

export function MedicationTab({ alerts }) {
  if (!alerts || alerts.length === 0) {
    return html`
      <div class="card">
        <p class="muted">No medication safety alerts were triggered for this consultation.</p>
      </div>
    `;
  }

  return html`
    <div>
      ${alerts.map((alert, idx) => html`
        <article class="card" key=${idx}>
          <div class="hyp-head">
            <h3>${alert.medicines.map((m) => m.label).join(" + ")}</h3>
            <span class=${`badge ${alert.severity === "high" ? "triage-Emergency" : "triage-Referral"}`}>
              ${alert.severity} severity
            </span>
          </div>
          <p class="small">
            <strong>Context:</strong>
            ${alert.disease ? ` Suspected ${alert.disease.label}` : " Drug-drug interaction"}
          </p>
          <p>${alert.reason}</p>
          ${alert.alternatives && alert.alternatives.length > 0
            ? html`
                <p class="small">
                  <strong>Safer alternatives to discuss with a clinician:</strong>
                  ${alert.alternatives.map((a) => ` ${a.label}`).join(", ")}
                </p>
              `
            : null}
        </article>
      `)}
    </div>
  `;
}
