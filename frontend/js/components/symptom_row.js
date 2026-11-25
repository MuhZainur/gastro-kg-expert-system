import { html } from "../../vendor/htm-preact-standalone.module.js";
import { certaintyWords } from "../format.js";

export function SymptomRow({ symptom, value, onChange }) {
  const answer = value?.answer || "skip";
  const certainty = value?.certainty ?? 0.8;

  const setAnswer = (next) => {
    onChange(symptom.id, { answer: next, certainty });
  };

  const setCertainty = (e) => {
    onChange(symptom.id, { answer, certainty: Number(e.target.value) });
  };

  return html`
    <div class="symptom-row" data-symptom-id=${symptom.id}>
      <div class="symptom-head">
        <div class="symptom-title">
          <strong>${symptom.code} · ${symptom.label}</strong>
          ${symptom.level === "emergency"
            ? html` <span class="badge triage-Emergency">Emergency sign</span>`
            : symptom.level === "alarm"
            ? html` <span class="badge triage-Urgent">Warning sign</span>`
            : null}
          <span class="symptom-id-label">${symptom.labelId}</span>
        </div>
        <div class="segmented" role="group" aria-label=${`Response for ${symptom.label}`}>
          <button
            type="button"
            aria-pressed=${answer === "yes" ? "true" : "false"}
            onClick=${() => setAnswer("yes")}
          >
            Yes
          </button>
          <button
            type="button"
            aria-pressed=${answer === "no" ? "true" : "false"}
            onClick=${() => setAnswer("no")}
          >
            No
          </button>
          <button
            type="button"
            aria-pressed=${answer === "skip" ? "true" : "false"}
            onClick=${() => setAnswer("skip")}
          >
            Skip
          </button>
        </div>
      </div>

      ${answer !== "skip"
        ? html`
            <div class="certainty-box">
              <label for=${`cf-${symptom.id}`} class="small">
                <strong>How sure are you?</strong>
              </label>
              <input
                id=${`cf-${symptom.id}`}
                type="range"
                min="0.1"
                max="1.0"
                step="0.1"
                value=${certainty.toFixed(1)}
                onInput=${setCertainty}
              />
              <span class="small">
                <strong>${certainty.toFixed(1)}</strong> (${certaintyWords(certainty)})
              </span>
            </div>
          `
        : null}
    </div>
  `;
}
