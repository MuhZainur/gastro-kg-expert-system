import { html, useState } from "../../vendor/htm-preact-standalone.module.js";
import { certaintyWords, formatCf } from "../format.js";

export function AdviceTab({ recommendations, nextQuestion, triage, onAnswerQuestion, busy }) {
  const [answer, setAnswer] = useState("yes");
  const [certainty, setCertainty] = useState(0.8);

  return html`
    <div>
      <section class="card">
        <h3>Clinical recommendations & examinations</h3>
        ${recommendations && recommendations.length > 0
          ? html`
              <ul>
                ${recommendations.map((rec, idx) => html`
                  <li key=${idx}>
                    <p>${rec.text}</p>
                    ${rec.examinations && rec.examinations.length > 0
                      ? html`<p class="small muted">Suggested examinations: ${rec.examinations.join(", ")}</p>`
                      : null}
                  </li>
                `)}
              </ul>
            `
          : html`<p class="muted">No additional clinical recommendations apply to this consultation.</p>`}
      </section>

      <section class="card">
        <h3>Next discriminating question</h3>
        ${nextQuestion
          ? html`
              <div>
                <p>
                  <strong>${nextQuestion.code} · ${nextQuestion.label}</strong>
                  <span class="symptom-id-label">${nextQuestion.labelId}</span>
                </p>
                <p class="small muted">
                  Discrimination score between top two hypotheses: ${formatCf(nextQuestion.score)}
                </p>
                <div class="row-actions">
                  <div class="segmented" role="group" aria-label="Next question answer">
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
                  </div>
                </div>
                <div class="certainty-box">
                  <label for="next-q-cf" class="small"><strong>How sure are you?</strong></label>
                  <input
                    id="next-q-cf"
                    type="range"
                    min="0.1"
                    max="1.0"
                    step="0.1"
                    value=${certainty.toFixed(1)}
                    onInput=${(e) => setCertainty(Number(e.target.value))}
                  />
                  <span class="small">
                    <strong>${certainty.toFixed(1)}</strong> (${certaintyWords(certainty)})
                  </span>
                </div>
                <div class="row-actions">
                  <button
                    type="button"
                    class="btn btn-primary"
                    disabled=${busy}
                    onClick=${() => onAnswerQuestion(nextQuestion.id, answer, certainty)}
                  >
                    ${busy ? "Running..." : "Submit answer and run again"}
                  </button>
                </div>
              </div>
            `
          : html`
              <p class="muted">
                ${triage && triage.level === "Emergency"
                  ? "No follow-up question is asked because emergency warning signs require immediate medical care."
                  : "No further discriminating question is available for this case."}
              </p>
            `}
      </section>
    </div>
  `;
}
