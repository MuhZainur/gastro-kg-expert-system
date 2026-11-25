import { html, render, useEffect, useRef, useState } from "../vendor/htm-preact-standalone.module.js";
import { Header } from "./components/header.js";
import { AboutView } from "./views/about.js";
import { ConsultView } from "./views/consult.js";
import { HomeView } from "./views/home.js";
import { QueriesView } from "./views/queries.js";
import { ResultView } from "./views/result.js";
import { RulesView } from "./views/rules.js";

function parseHash() {
  const raw = window.location.hash || "#/";
  const stripped = raw.startsWith("#") ? raw.slice(1) : raw;
  const [pathPart, queryPart] = stripped.split("?", 2);
  const route = pathPart || "/";
  const params = new URLSearchParams(queryPart || "");
  return { route, params };
}

function NotFoundView() {
  return html`
    <div>
      <h1 tabindex="-1">Page not found</h1>
      <div class="card">
        <p>The requested page does not exist.</p>
        <a class="btn btn-primary" href="#/">Return home</a>
      </div>
    </div>
  `;
}

function App() {
  const [loc, setLoc] = useState(parseHash);
  const [liveMsg, setLiveMsg] = useState("");
  const mainRef = useRef(null);

  useEffect(() => {
    const onHashChange = () => setLoc(parseHash());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  useEffect(() => {
    const heading = mainRef.current?.querySelector("h1");
    if (heading) {
      heading.focus();
      setLiveMsg(`Navigated to ${heading.textContent}`);
    }
  }, [loc.route, loc.params.toString()]);

  const navigate = (hash) => {
    if (window.location.hash === hash) {
      setLoc(parseHash());
    } else {
      window.location.hash = hash;
    }
  };

  let view;
  if (loc.route === "/" || loc.route === "") {
    view = html`<${HomeView} />`;
  } else if (loc.route === "/consult") {
    view = html`<${ConsultView} onNavigate=${navigate} />`;
  } else if (loc.route === "/result") {
    view = html`<${ResultView} caseParam=${loc.params.get("case")} onNavigate=${navigate} />`;
  } else if (loc.route === "/rules") {
    view = html`<${RulesView} onNavigate=${navigate} />`;
  } else if (loc.route === "/queries") {
    view = html`<${QueriesView} />`;
  } else if (loc.route === "/about") {
    view = html`<${AboutView} />`;
  } else {
    view = html`<${NotFoundView} />`;
  }

  return html`
    <div>
      <${Header} route=${loc.route} />
      <div class="sr-only" aria-live="polite">${liveMsg}</div>
      <main id="main-content" class="container" ref=${mainRef}>
        ${view}
      </main>
      <footer class="site-footer">
        <div class="footer-inner">
          <span>GastroKG · Educational prototype, not a medical device</span>
          <span>No patient data stored</span>
        </div>
      </footer>
    </div>
  `;
}

render(html`<${App} />`, document.getElementById("app"));
