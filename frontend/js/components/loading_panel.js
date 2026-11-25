import { html, useEffect, useState } from "../../vendor/htm-preact-standalone.module.js";
import { SLOW_NOTICE_MS } from "../config.js";

export function LoadingPanel({ label = "Running knowledge-graph reasoning..." }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const started = Date.now();
    const timer = setInterval(() => {
      setElapsed(Math.floor((Date.now() - started) / 1000));
    }, 500);
    return () => clearInterval(timer);
  }, []);

  const slow = elapsed * 1000 >= SLOW_NOTICE_MS;

  return html`
    <div class="card loading-box" role="status" aria-live="polite">
      <div class="spinner" aria-hidden="true"></div>
      <div>
        <div><strong>${label}</strong> (${elapsed}s)</div>
        ${slow ? html`<div class="small muted">The server is waking up; reasoning may take a few seconds.</div>` : null}
      </div>
    </div>
  `;
}
