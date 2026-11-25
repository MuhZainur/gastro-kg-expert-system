import { html, useEffect, useState } from "../../vendor/htm-preact-standalone.module.js";
import { getSampleIndex } from "../api.js";
import { formatCf, statusText, triageClass } from "../format.js";

export function HomeView() {
  const [cases, setCases] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    getSampleIndex()
      .then(setCases)
      .catch((err) => setError(err.message || "Could not load sample cases."));
  }, []);

  return html`
    <div>
      <h1 tabindex="-1">GastroKG: Stomach Disease Screening</h1>
      <p>
        An educational knowledge-graph expert system combining OWL 2 RL ontology reasoning,
        SHACL data validation, and 30 SPARQL CONSTRUCT rules with MYCIN certainty factors.
      </p>

      <div class="notice notice-warn" role="note">
        <strong>Educational prototype, not a medical device.</strong>
        <span> Certainty weights are illustrative and have not been clinically validated. All sample cases are synthetic.</span>
      </div>

      <p>
        <a class="btn btn-primary" href="#/consult">Start consultation</a>
      </p>

      <h2>13 Synthetic Sample Cases</h2>
      <p class="small muted">Precomputed offline from the knowledge graph so they open immediately even if the API is sleeping.</p>

      ${error ? html`<div class="notice notice-error">${error}</div>` : null}

      <div class="grid-cards">
        ${cases.map((item) => html`
          <article class="card case-card" key=${item.id}>
            <div>
              <div class="hyp-head">
                <strong>${item.id}</strong>
                ${item.triage
                  ? html`<span class=${`badge ${triageClass(item.triage.level)}`}>${item.triage.label}</span>`
                  : null}
              </div>
              <h3>${item.title}</h3>
              ${item.topDisease
                ? html`
                    <p class="small muted">
                      Top rank: <strong>${item.topDisease.label}</strong> (${formatCf(item.topDisease.cf)}, ${statusText(item.topDisease.status)})
                    </p>
                  `
                : null}
            </div>
            <div>
              <a class="btn btn-sm" href=${`#/result?case=${encodeURIComponent(item.id)}`}>Open result</a>
            </div>
          </article>
        `)}
      </div>
    </div>
  `;
}
