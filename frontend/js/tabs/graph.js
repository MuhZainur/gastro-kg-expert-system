import { html, useEffect, useRef } from "../../vendor/htm-preact-standalone.module.js";

const ORIGIN = {
  f: { name: "Asserted", hint: "TTL or input", colour: "#9aa7b5", dash: "" },
  d: { name: "RDFS", hint: "subClassOf, domain, range", colour: "#34c99a", dash: "7 4" },
  o: { name: "OWL", hint: "inverse, chain, class def", colour: "#a99bff", dash: "7 4" },
  r: { name: "Rule", hint: "SPARQL CONSTRUCT", colour: "#ff8a4c", dash: "2 4" },
};

const KIND = {
  patient: ["#0019a5", "Patient"],
  encounter: ["#0a2266", "Encounter"],
  symptom: ["#1b3252", "Symptom"],
  disease: ["#2c167c", "Disease"],
  drug: ["#751570", "Medication"],
  triage: ["#12406b", "Triage"],
  hypothesis: ["#5b1a86", "Hypothesis"],
  other: ["#343c5c", "Individual"],
  class: ["#10182b", "Class"],
};

const R = 42;
const BATCH = 8;
/* On small screens the first view keeps at least this zoom so labels stay readable. */
const MIN_SCALE = 0.85;
const MAX_SCALE = 1.25;
const NARROW = 640;
const PATIENT_CLASSES = ["gk:NSAIDUser", "gk:UlcerRiskPatient", "gk:AnticoagulantUser", "gk:HPyloriHistoryPatient"];
const ENCOUNTER_CLASSES = ["gk:EmergencyEncounter", "gk:AlarmEncounter"];
/* Heights of the class column, by number of classes. */
const CLASS_SLOTS = {
  1: [200],
  2: [200, 440],
  3: [20, 220, 440],
  4: [-60, 130, 330, 540],
  5: [-60, 130, 330, 540, 750],
  6: [-260, -60, 130, 330, 540, 750],
};

const bare = (id) => id.slice(id.indexOf(":") + 1);
const words = (text) => text.split(/[_ ]+|(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])/).filter(Boolean);

const makeSvg = (tag, attrs = {}, parent = null) => {
  const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [k, v] of Object.entries(attrs)) {
    el.setAttribute(k, String(v));
  }
  if (parent) parent.append(el);
  return el;
};

const makeHtml = (tag, text, parent, cls) => {
  const el = document.createElement(tag);
  if (text !== null && text !== undefined) el.textContent = text;
  if (cls) el.className = cls;
  if (parent) parent.append(el);
  return el;
};

export function GraphTab({ graph }) {
  const mountRef = useRef(null);

  useEffect(() => {
    const root = mountRef.current;
    if (!root || !graph) return;
    root.replaceChildren();

    const DATA = graph;
    const touching = new Map();
    for (const t of DATA.triples) {
      for (const end of [t[0], t[2]]) {
        if (!touching.has(end)) touching.set(end, []);
        touching.get(end).push(t);
      }
    }

    const shell = makeHtml("div", null, root, "graph-shell");
    const toolbar = makeHtml("div", null, shell, "graph-toolbar");
    const keysWrap = makeHtml("div", null, toolbar, "row-actions");
    const tools = makeHtml("div", null, toolbar, "graph-tools");
    const fitBtn = makeHtml("button", "Fit view", tools);
    fitBtn.type = "button";
    const resetBtn = makeHtml("button", "Reset", tools);
    resetBtn.type = "button";

    const zoomOutBtn = makeHtml("button", "−", tools, "graph-zoom");
    zoomOutBtn.type = "button";
    zoomOutBtn.setAttribute("aria-label", "Zoom out");
    const zoomInBtn = makeHtml("button", "+", tools, "graph-zoom");
    zoomInBtn.type = "button";
    zoomInBtn.setAttribute("aria-label", "Zoom in");

    const stage = makeHtml("div", null, shell, "graph-stage");
    const svg = makeSvg("svg", { class: "graph-svg", role: "group", "aria-label": "Knowledge graph explorer" }, stage);
    const defs = makeSvg("defs", {}, svg);
    const layer = makeSvg("g", {}, svg);
    const panel = makeHtml("aside", null, stage, "graph-panel");
    panel.hidden = true;

    const shown = { f: true, d: true, o: true, r: true };
    let visible = new Map();
    let selected = null;
    let drawn = [];
    let elements = new Map();
    let view = { x: 0, y: 0, w: 1200, h: 650 };

    const outs = (s, p) => (touching.get(s) || []).filter((t) => t[0] === s && t[1] === p).map((t) => t[2]);
    const ins = (o, p) => (touching.get(o) || []).filter((t) => t[2] === o && t[1] === p).map((t) => t[0]);
    const kindOf = (id) => DATA.nodes[id]?.[0] || "other";
    const valueOf = (id, key) => (DATA.nodes[id]?.[3] || []).find((v) => v[0] === key)?.[1];
    const focusName = bare(DATA.focus);
    /* Records the reasoner creates for this visit are named "<visit id>_...". */
    const isRecord = (id) => bare(id).startsWith(`${focusName}_`);

    /* Readable name of a node: { head, detail }. Internal record ids are never shown as names. */
    function describe(id) {
      const labelOfNode = (other) => (other ? DATA.nodes[other]?.[1] || words(bare(other)).join(" ") : "");
      const shortOf = (other) => (other ? words(bare(other)).join(" ") : "");
      const type = outs(id, "type");
      const has = (name) => type.includes(`gk:${name}`);

      if (kindOf(id) === "encounter") return { head: "Visit", detail: /^E\d+$/.test(bare(id)) ? bare(id) : "(current)" };
      if (kindOf(id) === "patient") return { head: "Patient", detail: /^PT\d+$/.test(bare(id)) ? bare(id) : "" };
      const link = (predicate) => outs(id, predicate)[0];
      /* the part of a record label after "<visit> advice: " or "<visit> triage: " */
      const afterColon = () => labelOfNode(id).split(": ").pop();
      const named = (head, others) => {
        const present = others.filter(Boolean);
        return {
          head,
          detail: present.map(shortOf).join(" "),
          full: present.length ? `${head}: ${present.map(labelOfNode).join(" / ")}` : head,
        };
      };
      if (has("SafetyAlert")) return named("Alert", [...outs(id, "concernsMedication"), link("forDisease")]);
      if (has("EvidenceItem")) {
        const observation = link("basedOnObservation");
        const symptom = observation && (outs(observation, "observedSymptom")[0] || outs(observation, "deniedSymptom")[0]);
        const hypothesis = link("ofHypothesis");
        return named("Evidence", [symptom, hypothesis && outs(hypothesis, "forDisease")[0]]);
      }
      if (has("TriageDecision")) return { head: "Triage", detail: afterColon(), full: `Triage reason: ${afterColon()}` };
      if (has("Recommendation")) return { head: "Advice", detail: afterColon(), full: `Advice: ${afterColon()}` };
      let found = null;
      if (has("Hypothesis")) found = ["Hypothesis", link("forDisease")];
      else if (has("SymptomObservation")) {
        const denied = link("deniedSymptom");
        found = [denied ? "Denied" : "Answer", denied || link("observedSymptom")];
      } else if (has("QuestionSuggestion")) found = ["Ask about", link("askSymptom")];
      else if (has("RuleMatch") || has("RuleFiring")) found = ["Rule match", link("evaluatesRule") || link("firedRule")];
      else if (has("EvidenceLink")) found = ["Evidence weight", link("aboutSymptom")];
      else if (has("DrugCaution")) found = ["Drug caution", link("cautionDrugClass")];
      else if (has("DrugInteraction")) found = ["Interaction", link("interactionBetween")];
      else if (has("DiagnosticRule")) return { head: "Rule", detail: bare(id), full: labelOfNode(id) };

      if (found) {
        const [head, other] = found;
        return { head, detail: shortOf(other), full: other ? `${head}: ${labelOfNode(other)}` : head };
      }
      return { head: "", detail: words(bare(id)).join(" "), full: labelOfNode(id) };
    }

    const shortName = (id) => {
      const { head, detail } = describe(id);
      return [head, detail].filter(Boolean).join(" ");
    };
    const fullName = (id) => describe(id).full || shortName(id);

    /* A live consultation gets random visit and patient ids; keep them out of the explanations. */
    const patientName = bare(outs(DATA.focus, "encounterOf")[0] || ":");
    function readable(text) {
      let out = text;
      if (patientName && !/^PT\d+$/.test(patientName)) out = out.split(patientName).join("this patient");
      if (!/^E\d+$/.test(focusName)) out = out.split(focusName).join("this visit");
      return out;
    }

    function neighbours(id) {
      const base = (t) => (t[1] === "type" && t[0] === id ? 0 : t[1] === "subClassOf" ? 1 : t[1] === "type" ? 3 : 2);
      /* named things first, per-visit records last */
      const rank = (t) => base(t) + (isRecord(t[0] === id ? t[2] : t[0]) ? 10 : 0);
      const list = (touching.get(id) || []).filter((t) => shown[t[3]]);
      list.sort((a, b) => rank(a) - rank(b) || "fdor".indexOf(a[3]) - "fdor".indexOf(b[3]));
      return [...new Set(list.map((t) => (t[0] === id ? t[2] : t[0])))];
    }

    const hiddenAround = (id) => neighbours(id).filter((other) => !visible.has(other));

    function placeAround(parent, ids) {
      const origin = visible.get(parent);
      const others = [...visible.values()];
      const cx = others.reduce((s, n) => s + n.x, 0) / others.length;
      const cy = others.reduce((s, n) => s + n.y, 0) / others.length;
      const base = Math.atan2(origin.y - cy, origin.x - cx || 1);
      const spread = Math.min(Math.PI * 1.8, ids.length * 0.62);
      ids.forEach((id, i) => {
        const angle = base - spread / 2 + (spread * (i + 0.5)) / ids.length;
        const distance = 190 + (i % 2) * 80;
        visible.set(id, {
          x: origin.x + Math.cos(angle) * distance,
          y: origin.y + Math.sin(angle) * distance,
          by: parent,
        });
      });
      for (let step = 0; step < 250; step++) {
        for (const id of ids) {
          const n = visible.get(id);
          for (const [other, o] of visible) {
            if (other === id) continue;
            const dx = n.x - o.x;
            const dy = n.y - o.y;
            const d = Math.hypot(dx, dy) || 1;
            if (d < 135) {
              n.x += ((dx || 1) / d) * (135 - d) * 0.2;
              n.y += (dy / d) * (135 - d) * 0.2;
            }
          }
        }
      }
    }

    function expand(id) {
      const ids = hiddenAround(id).slice(0, BATCH);
      if (ids.length) placeAround(id, ids);
      selected = id;
      renderGraph();
      frame(id);
      select(id);
    }

    const openedBy = (id) =>
      [...visible]
        .filter(([, n]) => {
          for (let by = n.by; by; by = visible.get(by)?.by) {
            if (by === id) return true;
          }
          return false;
        })
        .map(([other]) => other);

    function collapse(id) {
      openedBy(id).forEach((other) => visible.delete(other));
      selected = id;
      renderGraph();
      frame(id);
      select(id);
    }

    function hide(id) {
      [...openedBy(id), id].forEach((other) => visible.delete(other));
      selected = null;
      renderGraph();
      select(null);
    }

    function wrap(text) {
      const lines = [];
      for (const word of text.split(" ").filter(Boolean)) {
        if (lines.length && lines[lines.length - 1].length + word.length < 11) lines[lines.length - 1] += ` ${word}`;
        else lines.push(word);
      }
      return lines;
    }

    function labelLines(id) {
      const { head, detail } = describe(id);
      const lines = [...wrap(head), ...wrap(detail)];
      const cf = valueOf(id, "certaintyFactor");
      const out = lines.slice(0, cf === undefined ? 4 : 3).map((l) => (l.length > 13 ? `${l.slice(0, 12)}…` : l));
      if (lines.length > out.length) out[out.length - 1] += "…";
      if (cf !== undefined) out.push(`CF ${Number(cf).toFixed(3)}`);
      return out;
    }

    function drawEdge(edge) {
      const a = visible.get(edge.a);
      const b = visible.get(edge.b);
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const len = Math.hypot(dx, dy) || 1;
      const ux = dx / len;
      const uy = dy / len;
      for (const line of [edge.line, edge.hit]) {
        line.setAttribute("x1", a.x + ux * R);
        line.setAttribute("y1", a.y + uy * R);
        line.setAttribute("x2", b.x - ux * R);
        line.setAttribute("y2", b.y - uy * R);
      }
      let angle = (Math.atan2(dy, dx) * 180) / Math.PI;
      if (angle > 90) angle -= 180;
      else if (angle < -90) angle += 180;
      const t = edge.t || 0.5;
      edge.text.setAttribute("transform", `translate(${a.x + dx * t} ${a.y + dy * t}) rotate(${angle}) translate(0 -5)`);
    }

    /* Slide each edge caption along its line to where it collides least with other captions and nodes. */
    function placeLabels() {
      const taken = [];
      const nodes = [...visible.values()];
      const span = (e) => Math.hypot(visible.get(e.b).x - visible.get(e.a).x, visible.get(e.b).y - visible.get(e.a).y);
      for (const edge of [...drawn].sort((p, q) => span(p) - span(q))) {
        const a = visible.get(edge.a);
        const b = visible.get(edge.b);
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const len = span(edge) || 1;
        const width = edge.text.getComputedTextLength() || 80;
        const steps = Math.max(2, Math.ceil(width / 12));
        let best = null;
        for (const t of [0.5, 0.4, 0.6, 0.32, 0.68, 0.24, 0.76]) {
          const points = [];
          for (let i = 0; i <= steps; i++) {
            const along = (i / steps - 0.5) * width;
            points.push([a.x + dx * t + (dx / len) * along, a.y + dy * t + (dy / len) * along]);
          }
          let score = Math.abs(t - 0.5);
          for (const [x, y] of points) {
            for (const [px, py] of taken) if (Math.hypot(x - px, y - py) < 16) score += 1;
            for (const n of nodes) if (Math.hypot(x - n.x, y - n.y) < R + 6) score += 3;
          }
          if (!best || score < best.score) best = { t, score, points };
        }
        edge.t = best.t;
        taken.push(...best.points);
        drawEdge(edge);
      }
    }

    function move(id) {
      const n = visible.get(id);
      elements.get(id).setAttribute("transform", `translate(${n.x} ${n.y})`);
    }

    function drawMenu() {
      layer.querySelectorAll(".menu").forEach((m) => m.remove());
      if (!selected || !visible.has(selected)) return;
      const n = visible.get(selected);
      const hidden = hiddenAround(selected).length;
      const opened = openedBy(selected).length;
      const items = [
        ["+", "Expand", -90, () => expand(selected), hidden],
        ["−", "Collapse", -35, () => collapse(selected), opened],
        ["×", "Hide", -145, () => hide(selected), 1],
      ];
      for (const [symbol, title, degrees, action, available] of items) {
        if (!available) continue;
        const angle = (degrees * Math.PI) / 180;
        const g = makeSvg(
          "g",
          {
            class: "menu",
            role: "button",
            tabindex: "0",
            "aria-label": title,
            transform: `translate(${n.x + Math.cos(angle) * (R + 17)} ${n.y + Math.sin(angle) * (R + 17)})`,
          },
          layer
        );
        makeSvg("title", {}, g).textContent = title;
        makeSvg("circle", { r: 15 }, g);
        makeSvg("text", { y: 5 }, g).textContent = symbol;
        g.addEventListener("pointerdown", (ev) => ev.stopPropagation());
        g.addEventListener("click", (ev) => {
          ev.stopPropagation();
          action();
        });
        g.addEventListener("keydown", (ev) => {
          if (ev.key === "Enter" || ev.key === " ") {
            ev.preventDefault();
            action();
          }
        });
      }
    }

    function tripleRow(t, withAxiom) {
      const row = makeHtml("div", null, panel, "graph-row");
      makeHtml("span", ORIGIN[t[3]].name, row, `origin-tag ${t[3]}`);
      row.append(`${shortName(t[0])}  —  ${t[1]}  →  ${shortName(t[2])}`);
      makeHtml("div", readable(DATA.reasons[t[4]]), row, "small muted");
      if (withAxiom) {
        const key = t[1] === "type" || t[1] === "subClassOf" ? t[2] : t[1];
        if (DATA.axioms[key]) makeHtml("pre", DATA.axioms[key], row);
      }
    }

    function select(id, pair) {
      selected = id;
      const list = pair ? pair.list : id ? (touching.get(id) || []).filter((t) => shown[t[3]]) : [];
      const active = Boolean(id || pair);
      const near = new Set(pair ? [pair.a, pair.b] : id ? [id, ...neighbours(id)] : []);
      for (const [other, g] of elements) {
        g.classList.toggle("dim", active && !near.has(other));
        g.classList.toggle("on", other === id);
      }
      for (const e of drawn) {
        e.g.classList.toggle("dim", active && !(pair ? e.a === pair.a && e.b === pair.b : e.a === id || e.b === id));
      }
      drawMenu();
      panel.hidden = !active;
      panel.replaceChildren();
      panel.scrollTop = 0;
      if (!active) return;
      /* on a phone the panel covers the lower half: lift the chosen node above it */
      const node = id && visible.get(id);
      if (node && svg.getBoundingClientRect().width <= NARROW && node.y > view.y + view.h * 0.42) {
        view.y = node.y - view.h * 0.25;
        applyView();
      }

      const close = makeHtml("button", "×", panel, "graph-panel-close");
      close.type = "button";
      close.setAttribute("aria-label", "Close details");
      close.onclick = () => select(null);

      if (pair) {
        makeHtml("h2", `${shortName(pair.a)} & ${shortName(pair.b)}`, panel);
        makeHtml("h3", "Relations, provenance, and T-Box axioms", panel);
        list.forEach((t) => tripleRow(t, true));
        return;
      }

      const [kind, , idLabel, values] = DATA.nodes[id] || ["other", "", "", []];
      makeHtml("h2", fullName(id), panel);
      makeHtml("div", [KIND[kind]?.[1] || "Node", idLabel].filter(Boolean).join(" · "), panel, "small");
      makeHtml("div", `Graph IRI: ${id}`, panel, "small muted");

      const actions = makeHtml("div", null, panel, "row-actions");
      const hidden = hiddenAround(id).length;
      for (const [label, action, enabled] of [
        [`+ Expand (${hidden})`, () => expand(id), hidden > 0],
        ["− Collapse", () => collapse(id), openedBy(id).length > 0],
        ["× Hide", () => hide(id), visible.has(id)],
      ]) {
        const btn = makeHtml("button", label, actions, "btn btn-sm");
        btn.type = "button";
        btn.disabled = !enabled;
        btn.onclick = action;
      }

      const types = list.filter((t) => t[0] === id && (t[1] === "type" || t[1] === "subClassOf"));
      if (types.length) {
        makeHtml("h3", kind === "class" ? "Sub-class of" : "Types (rdf:type)", panel);
        types.forEach((t) => tripleRow(t, false));
      }
      if (values.length) {
        makeHtml("h3", "Properties", panel);
        values.forEach(([p, v]) => {
          const row = makeHtml("div", `${p}: ${v}`, panel, "graph-row");
          void row;
        });
      }
      if (DATA.axioms[id]) {
        makeHtml("h3", "T-Box definition", panel);
        makeHtml("pre", DATA.axioms[id], panel);
      }
      const rest = list.filter((t) => !types.includes(t));
      if (rest.length) {
        makeHtml("h3", `Other relations (${rest.length})`, panel);
        rest.slice(0, 40).forEach((t) => tripleRow(t, false));
      }
    }

    function applyView() {
      svg.setAttribute("viewBox", `${view.x} ${view.y} ${view.w} ${view.h}`);
    }

    /* Show the graph. With a node id, never zoom out below the readable minimum: centre on that
       node and let the user pan. Without one ("Fit view"), show everything. */
    function frame(centreId, shift = 0) {
      const list = [...visible.values()];
      if (!list.length) return;
      const x0 = Math.min(...list.map((n) => n.x)) - 60;
      const x1 = Math.max(...list.map((n) => n.x)) + 60;
      const y0 = Math.min(...list.map((n) => n.y)) - 70;
      const y1 = Math.max(...list.map((n) => n.y)) + 55;
      const box = svg.getBoundingClientRect();
      const width = box.width || 960;
      const height = box.height || 560;
      const usable = selected && width > 780 ? width - 390 : width;
      let scale = Math.min(usable / (x1 - x0), height / (y1 - y0), MAX_SCALE);
      let cx = (x0 + x1) / 2;
      let cy = (y0 + y1) / 2;
      const node = centreId && visible.get(centreId);
      if (node && scale < MIN_SCALE) {
        scale = MIN_SCALE;
        const within = (v, low, high) => (low > high ? (low + high) / 2 : Math.max(low, Math.min(high, v)));
        const halfW = usable / scale / 2;
        const halfH = height / scale / 2;
        cx = within(node.x + (width <= NARROW ? shift : 0), x0 + halfW, x1 - halfW);
        cy = within(node.y, y0 + halfH, y1 - halfH);
      }
      view = { x: cx - usable / scale / 2, y: cy - height / scale / 2, w: width / scale, h: height / scale };
      applyView();
    }

    function zoom(factor, centre) {
      const at = centre || { x: view.x + view.w / 2, y: view.y + view.h / 2 };
      const w = Math.max(300, Math.min(9000, view.w * factor));
      const f = w / view.w;
      view = { x: at.x - (at.x - view.x) * f, y: at.y - (at.y - view.y) * f, w, h: view.h * f };
      applyView();
    }

    let drag = null;
    let last = { id: null, time: 0 };

    const svgPoint = (ev) => {
      const ctm = svg.getScreenCTM();
      return ctm ? new DOMPoint(ev.clientX, ev.clientY).matrixTransform(ctm.inverse()) : { x: 0, y: 0 };
    };

    function renderGraph() {
      layer.replaceChildren();
      elements = new Map();
      const pairs = new Map();
      for (const t of DATA.triples) {
        if (!shown[t[3]] || !visible.has(t[0]) || !visible.has(t[2])) continue;
        const key = t[0] < t[2] ? `${t[0]}|${t[2]}` : `${t[2]}|${t[0]}`;
        if (!pairs.has(key)) pairs.set(key, { a: t[0], b: t[2], list: [] });
        pairs.get(key).list.push(t);
      }
      drawn = [...pairs.values()].map((pair) => {
        const origins = [..."dor"].filter((k) => pair.list.some((t) => t[3] === k));
        const style = origins.length ? origins[origins.length - 1] : "f";
        const g = makeSvg("g", { class: `edge ${style}` }, layer);
        const line = makeSvg("line", {}, g);
        const hit = makeSvg("line", { class: "hit" }, g);
        if (pair.list.some((t) => t[0] === pair.a)) line.setAttribute("marker-end", `url(#arrow-${style})`);
        if (pair.list.some((t) => t[0] === pair.b)) line.setAttribute("marker-start", `url(#arrow-${style})`);
        const text = makeSvg("text", pair.list.length > 1 ? { class: "many" } : {}, g);
        text.textContent = pair.list.length > 1 ? `${pair.list.length} predicates` : pair.list[0][1];
        for (const k of origins) makeSvg("tspan", { class: k }, text).textContent = ` · ${ORIGIN[k].name}`;
        g.addEventListener("pointerdown", (ev) => ev.stopPropagation());
        g.addEventListener("click", () => select(null, pair));
        return { ...pair, g, line, hit, text };
      });

      for (const id of visible.keys()) {
        const info = DATA.nodes[id] || ["other", bare(id), "", []];
        const g = makeSvg(
          "g",
          {
            class: `node${info[0] === "class" ? " cls" : ""}`,
            tabindex: "0",
            role: "button",
            "aria-label": `${fullName(id)}, ${KIND[info[0]]?.[1] || "Node"}`,
          },
          layer
        );
        makeSvg("circle", { r: R, fill: KIND[info[0]]?.[0] || "#343c5c" }, g);
        const lines = labelLines(id);
        lines.forEach((lineText, i) => {
          makeSvg("text", { y: 4 + (i - (lines.length - 1) / 2) * 15 }, g).textContent = lineText;
        });
        g.addEventListener("pointerdown", (ev) => {
          ev.stopPropagation();
          ev.preventDefault();
          const p = svgPoint(ev);
          const n = visible.get(id);
          drag = { id, dx: n.x - p.x, dy: n.y - p.y, x: ev.clientX, y: ev.clientY, moved: false };
        });
        g.addEventListener("keydown", (ev) => {
          if (ev.key === "Enter") select(id);
          if (ev.key === "+" || ev.key === "=") expand(id);
        });
        elements.set(id, g);
        move(id);
      }
      drawn.forEach(drawEdge);
      placeLabels();
    }

    /* The opening picture, in columns: patient classes | patient | visit and medicines |
       symptoms, drug class and top hypothesis | candidate diseases. */
    function startLayout() {
      const put = (id, x, y) => {
        if (id && DATA.nodes[id] && !visible.has(id)) visible.set(id, { x, y, by: null });
      };
      const encounter = DATA.focus;
      const patient = outs(encounter, "encounterOf")[0] || ins(encounter, "hadEncounter")[0];
      const hypotheses = ins(encounter, "ofEncounter")
        .filter((h) => kindOf(h) === "hypothesis")
        .sort((a, b) => Number(valueOf(a, "rank")) - Number(valueOf(b, "rank")) || a.localeCompare(b));
      const primary = outs(encounter, "primaryHypothesis")[0] || hypotheses[0];
      const triage = outs(encounter, "finalTriage")[0];

      put(encounter, 350, 320);
      put(patient, 110, 320);

      const symptoms = outs(encounter, "showsSymptom").slice(0, 6);
      symptoms.forEach((id, i) => put(id, 610, 225 + i * 115));

      /* lowest rank on top, so the leading disease sits next to its hypothesis */
      const diseases = [...new Set([primary, ...hypotheses].filter(Boolean).map((h) => outs(h, "forDisease")[0]))]
        .filter(Boolean)
        .slice(0, 3)
        .reverse();
      diseases.forEach((id, i) => put(id, 930, 485 - (diseases.length - 1 - i) * 122));
      put(primary, 610, Math.max(455, 225 + (symptoms.length - 1) * 115) + 115);

      put(triage, 350, 520);
      if (triage) put(outs(triage, "refersTo")[0], 110, 520);

      if (patient) {
        const alerted = ins(encounter, "ofEncounter").flatMap((a) => outs(a, "concernsMedication"));
        const medicines = [...new Set([...outs(patient, "takesRegularly"), ...outs(patient, "takesMedication")])]
          .sort((a, b) => Number(alerted.includes(b)) - Number(alerted.includes(a)) || a.localeCompare(b))
          .slice(0, 3);
        medicines.forEach((medicine, i) => {
          const y = 110 - i * 120;
          put(medicine, 350, y);
          const drugClass = outs(medicine, "drugClass")[0];
          if (!drugClass || visible.has(drugClass)) return;
          put(drugClass, 610, y);
          put(outs(drugClass, "saferAlternative").find((other) => !medicines.includes(other)), 930, y);
        });
      }

      const classes = [
        ...ENCOUNTER_CLASSES.filter((c) => outs(encounter, "type").includes(c)),
        ...PATIENT_CLASSES.filter((c) => patient && outs(patient, "type").includes(c)),
      ];
      /* top to bottom so related classes stay neighbours; far enough apart for a caption between */
      (CLASS_SLOTS[classes.length] || []).forEach((y, i) => put(classes[i], -120, y));
    }

    const home = () => frame(DATA.focus, 130);

    function reset() {
      visible = new Map();
      selected = null;
      select(null);
      if (DATA.nodes[DATA.focus]) startLayout();
      renderGraph();
      home();
    }

    for (const [key, o] of Object.entries(ORIGIN)) {
      const marker = makeSvg(
        "marker",
        { id: `arrow-${key}`, viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 8, markerHeight: 8, orient: "auto-start-reverse" },
        defs
      );
      makeSvg("path", { d: "M1 1L9 5L1 9", fill: "none", stroke: o.colour, "stroke-width": 1.4 }, marker);

      const btn = makeHtml("button", null, keysWrap, "graph-key");
      btn.type = "button";
      btn.setAttribute("aria-pressed", "true");
      btn.title = `${o.name}: ${o.hint}`;
      const sample = makeSvg("svg", { class: "graph-key-line", viewBox: "0 0 34 10" }, btn);
      makeSvg("line", { x1: 0, y1: 5, x2: 34, y2: 5, stroke: o.colour, "stroke-width": 2.5, "stroke-dasharray": o.dash }, sample);
      makeHtml("span", o.name, btn);
      btn.onclick = () => {
        shown[key] = !shown[key];
        btn.setAttribute("aria-pressed", String(shown[key]));
        renderGraph();
        select(selected && visible.has(selected) ? selected : null);
      };
    }

    const onSvgDown = (ev) => {
      drag = { id: null, x: ev.clientX, y: ev.clientY, moved: false };
    };
    const onMove = (ev) => {
      if (!drag) return;
      if (!drag.moved && Math.hypot(ev.clientX - drag.x, ev.clientY - drag.y) < 4) return;
      drag.moved = true;
      if (drag.id) {
        const p = svgPoint(ev);
        const n = visible.get(drag.id);
        n.x = p.x + drag.dx;
        n.y = p.y + drag.dy;
        move(drag.id);
        drawn.filter((e) => e.a === drag.id || e.b === drag.id).forEach(drawEdge);
        drawMenu();
      } else {
        const ctm = svg.getScreenCTM();
        const scale = ctm ? ctm.a : 1;
        view.x -= (ev.clientX - drag.x) / scale;
        view.y -= (ev.clientY - drag.y) / scale;
        drag.x = ev.clientX;
        drag.y = ev.clientY;
        applyView();
      }
    };
    const onUp = () => {
      if (drag && !drag.moved) {
        if (!drag.id) select(null);
        else if (last.id === drag.id && Date.now() - last.time < 400) {
          expand(drag.id);
          last = { id: null, time: 0 };
        } else {
          last = { id: drag.id, time: Date.now() };
          select(drag.id);
        }
      }
      drag = null;
    };
    const onWheel = (ev) => {
      ev.preventDefault();
      zoom(ev.deltaY < 0 ? 0.87 : 1.15, svgPoint(ev));
    };
    /* phones resize the window while scrolling; only a width change should move the graph */
    let lastWidth = stage.clientWidth;
    const onResize = () => {
      if (stage.clientWidth === lastWidth) return;
      lastWidth = stage.clientWidth;
      home();
    };

    svg.addEventListener("pointerdown", onSvgDown);
    svg.addEventListener("wheel", onWheel, { passive: false });
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    window.addEventListener("pointercancel", onUp);
    window.addEventListener("resize", onResize);
    fitBtn.onclick = () => frame();
    resetBtn.onclick = reset;
    zoomInBtn.onclick = () => zoom(0.8);
    zoomOutBtn.onclick = () => zoom(1.25);

    reset();

    return () => {
      svg.removeEventListener("pointerdown", onSvgDown);
      svg.removeEventListener("wheel", onWheel);
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("pointercancel", onUp);
      window.removeEventListener("resize", onResize);
    };
  }, [graph]);

  return html`
    <div>
      <p class="small muted">
        Tap a node or a line to see its details and why it exists. Use + to expand, − to collapse, × to hide; double-click also expands. Drag the background to move around; zoom with the + and − buttons or the mouse wheel.
      </p>
      <div ref=${mountRef}></div>
    </div>
  `;
}
