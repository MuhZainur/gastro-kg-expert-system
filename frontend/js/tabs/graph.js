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

const bare = (id) => id.slice(id.indexOf(":") + 1);

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

    function neighbours(id) {
      const rank = (t) => (t[1] === "type" && t[0] === id ? 0 : t[1] === "subClassOf" ? 1 : t[1] === "type" ? 3 : 2);
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
      fit();
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
      fit();
      select(id);
    }

    function hide(id) {
      [...openedBy(id), id].forEach((other) => visible.delete(other));
      selected = null;
      renderGraph();
      select(null);
    }

    function labelLines(id) {
      const words = bare(id).split(/_|(?<=[a-z0-9])(?=[A-Z])/);
      const lines = [];
      for (const word of words) {
        if (lines.length && (lines[lines.length - 1] + word).length <= 11) {
          lines[lines.length - 1] += (id.includes("_") ? "_" : "") + word;
        } else {
          lines.push(word);
        }
      }
      const cf = (DATA.nodes[id]?.[3] || []).find((v) => v[0] === "certaintyFactor");
      const out = lines.slice(0, cf ? 2 : 3).map((l) => (l.length > 13 ? `${l.slice(0, 12)}…` : l));
      if (lines.length > out.length) out[out.length - 1] += "…";
      if (cf) out.push(`CF ${Number(cf[1]).toFixed(3)}`);
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
      edge.text.setAttribute("transform", `translate(${a.x + dx * 0.5} ${a.y + dy * 0.5}) rotate(${angle}) translate(0 -5)`);
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
      row.append(`${bare(t[0])}  ${t[1]} →  ${bare(t[2])}`);
      const small = makeHtml("div", DATA.reasons[t[4]], row, "small muted");
      void small;
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
      if (!active) return;

      const close = makeHtml("button", "×", panel, "graph-panel-close");
      close.type = "button";
      close.setAttribute("aria-label", "Close details");
      close.onclick = () => select(null);

      if (pair) {
        makeHtml("h2", `${bare(pair.a)} & ${bare(pair.b)}`, panel);
        makeHtml("h3", "Relations, provenance, and T-Box axioms", panel);
        list.forEach((t) => tripleRow(t, true));
        return;
      }

      const [kind, en, idLabel, values] = DATA.nodes[id] || ["other", bare(id), "", []];
      makeHtml("h2", bare(id), panel);
      makeHtml("div", [KIND[kind]?.[1] || "Node", en, idLabel].filter(Boolean).join(" · "), panel, "small");

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

    function fit() {
      const list = [...visible.values()];
      if (!list.length) return;
      const x0 = Math.min(...list.map((n) => n.x)) - 75;
      const x1 = Math.max(...list.map((n) => n.x)) + 75;
      const y0 = Math.min(...list.map((n) => n.y)) - 80;
      const y1 = Math.max(...list.map((n) => n.y)) + 65;
      const box = svg.getBoundingClientRect();
      const width = box.width || 960;
      const height = box.height || 560;
      const usable = selected && width > 780 ? width - 390 : width;
      const ratio = usable / height;
      let w = Math.max(x1 - x0, 760);
      let h = y1 - y0;
      if (w / h < ratio) w = h * ratio;
      else h = w / ratio;
      view = { x: (x0 + x1 - w) / 2, y: (y0 + y1 - h) / 2, w: (w * width) / usable, h };
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
        const text = makeSvg("text", {}, g);
        text.textContent = pair.list.length > 1 ? `${pair.list.length} predicates` : pair.list[0][1];
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
            "aria-label": `${bare(id)}, ${KIND[info[0]]?.[1] || "Node"}`,
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
    }

    function reset() {
      visible = new Map();
      if (DATA.nodes[DATA.focus]) {
        visible.set(DATA.focus, { x: 400, y: 300, by: null });
        const firstBatch = hiddenAround(DATA.focus).slice(0, 10);
        if (firstBatch.length) placeAround(DATA.focus, firstBatch);
      }
      selected = null;
      renderGraph();
      select(null);
      fit();
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
      const p = svgPoint(ev);
      const factor = ev.deltaY < 0 ? 0.87 : 1.15;
      const w = Math.max(300, Math.min(9000, view.w * factor));
      const f = w / view.w;
      view = { x: p.x - (p.x - view.x) * f, y: p.y - (p.y - view.y) * f, w, h: view.h * f };
      applyView();
    };

    svg.addEventListener("pointerdown", onSvgDown);
    svg.addEventListener("wheel", onWheel, { passive: false });
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    window.addEventListener("resize", fit);
    fitBtn.onclick = fit;
    resetBtn.onclick = reset;

    reset();

    return () => {
      svg.removeEventListener("pointerdown", onSvgDown);
      svg.removeEventListener("wheel", onWheel);
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("resize", fit);
    };
  }, [graph]);

  return html`
    <div>
      <p class="small muted">
        Click a node to inspect or expand (+), collapse (−), or hide (×). Double-click expands neighbours. Drag nodes or background to pan; scroll to zoom.
      </p>
      <div ref=${mountRef}></div>
    </div>
  `;
}
