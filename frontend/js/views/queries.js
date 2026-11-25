import { html, useEffect, useState } from "../../vendor/htm-preact-standalone.module.js";
import { getQueries } from "../api.js";

export function QueriesView() {
  const [queries, setQueries] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    getQueries()
      .then(setQueries)
      .catch((err) => setError(err.message || "Could not load competency questions."));
  }, []);

  return html`
    <div>
      <h1 tabindex="-1">14 Competency Questions</h1>
      <p class="small muted">
        Stored SPARQL SELECT queries and precomputed results verified against both the Python engine and GraphDB 11.5.2.
        Free-form SPARQL queries are disabled on the public API and demonstrated locally in GraphDB.
      </p>

      ${error ? html`<div class="notice notice-error">${error}</div>` : null}

      ${queries.map((q) => html`
        <article class="card" key=${q.id}>
          <h2>${q.id.toUpperCase()}: ${q.title}</h2>
          <pre>${q.query}</pre>
          <div class="table-scroll">
            <table>
              <thead>
                <tr>
                  ${q.columns.map((col) => html`<th key=${col}>?${col}</th>`)}
                </tr>
              </thead>
              <tbody>
                ${q.rows.map((row, rIdx) => html`
                  <tr key=${rIdx}>
                    ${row.map((cell, cIdx) => html`<td key=${cIdx}>${cell === null ? "-" : String(cell)}</td>`)}
                  </tr>
                `)}
              </tbody>
            </table>
          </div>
        </article>
      `)}
    </div>
  `;
}
