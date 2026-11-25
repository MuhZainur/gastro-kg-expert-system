import { html } from "../../vendor/htm-preact-standalone.module.js";

export function ErrorPanel({ error, onRetry }) {
  if (!error) return null;

  let heading = "Could not complete request";
  let detail = error.message || "Unexpected error.";
  if (error.status === 429) {
    heading = "Too many requests";
    detail = "Too many requests, wait a minute.";
  } else if (error.status === 500) {
    heading = "Server error";
    detail = "The server encountered an internal error while processing your request.";
  } else if (error.status === 422) {
    heading = "Please check your input";
  }

  return html`
    <div class="notice notice-error" role="alert">
      <strong>${heading}</strong>
      <p>${detail}</p>
      ${error.errors && error.errors.length > 0 && error.status === 422
        ? html`
            <ul>
              ${error.errors.map((e, i) => html`
                <li key=${i}>
                  ${e.field ? html`<code>${e.field}</code>: ` : null}${e.message}
                </li>
              `)}
            </ul>
          `
        : null}
      ${error.requestId ? html`<p class="small">Reference ID: <code>${error.requestId}</code></p>` : null}
      <div class="row-actions">
        ${onRetry
          ? html`<button type="button" class="btn btn-sm" onClick=${onRetry}>Try again</button>`
          : null}
        <a class="btn btn-sm" href="#/">View sample cases</a>
      </div>
    </div>
  `;
}
