import { html } from "../../vendor/htm-preact-standalone.module.js";

export function ReasoningTab({ owlFacts, meta }) {
  return html`
    <div>
      <section class="card">
        <h3>Triple counts & measured timings</h3>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Stage</th>
                <th>Count / Duration</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Asserted triples (T-Box + A-Box + patient)</td>
                <td>${meta.asserted}</td>
              </tr>
              <tr>
                <td>After RDFS + OWL 2 RL closure</td>
                <td>${meta.afterClosure} (+${meta.afterClosure - meta.asserted})</td>
              </tr>
              <tr>
                <td>Inferred by SPARQL CONSTRUCT rules</td>
                <td>+${meta.inferred}</td>
              </tr>
              <tr>
                <td>SHACL validation</td>
                <td>${meta.seconds ? `${meta.seconds.shacl.toFixed(3)}s` : "Precomputed"}</td>
              </tr>
              <tr>
                <td>OWL 2 RL closure</td>
                <td>${meta.seconds ? `${meta.seconds.closure.toFixed(3)}s` : "Precomputed"}</td>
              </tr>
              <tr>
                <td>SPARQL rules</td>
                <td>${meta.seconds ? `${meta.seconds.rules.toFixed(3)}s` : "Precomputed"}</td>
              </tr>
              <tr>
                <td>Total reasoning pipeline</td>
                <td><strong>${meta.seconds ? `${meta.seconds.total.toFixed(3)}s` : "Precomputed"}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="card">
        <h3>OWL 2 RL & RDFS classifications on patient and encounter</h3>
        ${owlFacts && owlFacts.length > 0
          ? html`
              <div class="table-scroll">
                <table class="stack-table">
                  <thead>
                    <tr>
                      <th>Subject</th>
                      <th>Relation</th>
                      <th>Inferred value</th>
                      <th>Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${owlFacts.map((fact, idx) => html`
                      <tr key=${idx}>
                        <td data-label="Subject">${fact.subject.label}</td>
                        <td data-label="Relation" class="nowrap"><code>${fact.relation}</code></td>
                        <td data-label="Inferred value"><strong>${fact.value.label}</strong></td>
                        <td data-label="Reason" class="small">${fact.reason}</td>
                      </tr>
                    `)}
                  </tbody>
                </table>
              </div>
            `
          : html`<p class="muted">No watched OWL/RDFS classifications were triggered for this patient or encounter.</p>`}
      </section>
    </div>
  `;
}
