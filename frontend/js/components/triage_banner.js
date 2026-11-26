import { html } from "../../vendor/htm-preact-standalone.module.js";
import { triageClass, triageName } from "../format.js";

export function TriageBanner({ triage, meta }) {
  const modified = meta && ((meta.disabledRules && meta.disabledRules.length > 0) || meta.customKnowledge);

  return html`
    <div>
      ${modified
        ? html`
            <div class="notice notice-warn" role="status">
              <strong>Modified reasoning configuration:</strong>
              <span>
                ${meta.disabledRules && meta.disabledRules.length > 0
                  ? `${meta.disabledRules.length} rule(s) disabled. `
                  : ""}
                ${meta.customKnowledge ? "Custom knowledge is active. " : ""}
                This result differs from the standard system.
              </span>
            </div>
          `
        : null}

      ${!triage
        ? html`
            <div class="notice notice-warn" role="status">
              <strong>Triage unavailable:</strong> disabled rules removed the triage decision. This result differs from the standard system.
            </div>
          `
        : html`
            <section
              class=${`triage-banner ${triageClass(triage.level)} ${triage.level === "Emergency" ? "triage-banner-emergency" : ""}`}
              aria-label="Triage recommendation"
            >
              <h2>
                ${triage.level === "Emergency" ? "SEEK EMERGENCY CARE NOW — " : ""}
                ${triage.label}
              </h2>
              <p class="small">
                <span>${triage.labelId}</span> · <strong>Recommended facility:</strong> ${triage.facility}
              </p>
              ${triage.level === "Emergency"
                ? html`<p><strong>An emergency warning sign was reported. Do not wait; go to the ${triage.facility} immediately.</strong></p>`
                : null}
              ${triage.reasons && triage.reasons.length > 0
                ? html`
                    <ul class="small">
                      ${triage.reasons.map((r, idx) => html`
                        <li key=${idx}>
                          <strong>${triageName(r.level)}:</strong> ${r.reason}
                          ${r.triggeredBy && r.triggeredBy.length > 0
                            ? html` (Triggered by: ${r.triggeredBy.join(", ")})`
                            : null}
                        </li>
                      `)}
                    </ul>
                  `
                : null}
            </section>
          `}
    </div>
  `;
}
