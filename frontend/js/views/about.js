import { html } from "../../vendor/htm-preact-standalone.module.js";
import { ontologyDownloadUrl } from "../api.js";

const PIPELINE = [
  { title: "1. Patient Input", detail: "Validated by strict Pydantic schemas and vocabulary allow-lists." },
  { title: "2. RDF Triples", detail: "Built strictly via rdflib terms (patient, encounter, observations)." },
  { title: "3. SHACL Validation", detail: "Checks required fields, CF bounds, and rule shape constraints." },
  { title: "4. RDFS + OWL 2 RL", detail: "Expands class hierarchy, property chains, inverses, and defined classes." },
  { title: "5. 30 SPARQL Rules", detail: "Computes MYCIN certainty factors, rule coverage, alerts, triage, and next question." },
];

export function AboutView() {
  return html`
    <div>
      <h1 tabindex="-1">About GastroKG</h1>
      <p>
        GastroKG is a knowledge-graph expert system for screening upper gastrointestinal complaints,
        developed for the Principles of Artificial Intelligence final project (Magister Kecerdasan Artifisial, Universitas Gadjah Mada, 2026).
      </p>

      <h2>Reasoning pipeline</h2>
      <div class="flow-steps">
        ${PIPELINE.map((step) => html`
          <div class="flow-step" key=${step.title}>
            <strong>${step.title}</strong>
            <p class="small muted">${step.detail}</p>
          </div>
        `)}
      </div>

      <section class="card">
        <h2>Ontology & SHACL downloads (Turtle)</h2>
        <p class="small muted">Download the exact ontology files served by the API:</p>
        <div class="row-actions">
          <a class="btn btn-sm" href=${ontologyDownloadUrl("tbox")}>T-Box (gastrokg-tbox.ttl)</a>
          <a class="btn btn-sm" href=${ontologyDownloadUrl("knowledge")}>Knowledge A-Box (gastrokg-knowledge.ttl)</a>
          <a class="btn btn-sm" href=${ontologyDownloadUrl("cases")}>Synthetic Cases (gastrokg-cases.ttl)</a>
          <a class="btn btn-sm" href=${ontologyDownloadUrl("shapes")}>SHACL Shapes (gastrokg-shapes.ttl)</a>
        </div>
      </section>

      <section class="card">
        <h2>Limitations & security scope</h2>
        <ul>
          <li><strong>Educational prototype only:</strong> not a medical device; certainty weights are illustrative and not clinically validated.</li>
          <li><strong>Synthetic data:</strong> all 13 sample cases are synthetic; patient consultation answers live in memory only and are never stored.</li>
          <li><strong>No public SPARQL endpoint:</strong> free-form queries are restricted to local GraphDB; public custom knowledge is capped and allow-listed.</li>
        </ul>
      </section>

      <section class="card">
        <h2>Team</h2>
        <p>Hasnan Husaini · Muhammad Zainurrahman · Nur Sekti Waskitha Jati</p>
      </section>
    </div>
  `;
}
