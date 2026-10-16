"""The app served by loopwright serve, and the product site's playground when served with the site.

One page, talking only to the API. Sources: a ResPlan plan by id, an uploaded image, PDF or DXF, or
rooms drawn on a grid. Every change (door removed, rooms connected, room type changed, zone rule
switched) is re-solved by the server, so the drawing, the validator and the explanation always
describe the same design. Served with the site (`loopwright serve --site`), the page is the site's
playground: inside the site's own header and footer, dressed by its stylesheet, with a model view that
shows the design as the site's scale model, signal and all. Text from the server is only ever written with textContent; the model's SVG is
parsed as SVG, never written as HTML.
"""
import pathlib


LOOP = ("M573.0 265.0C556.2 283.2 540.1 301.7 522.7 319.5C505.3 337.2 487.9 355.2 468.6 371.6C449.3 387.9 429.3 404.3 "
        "407.0 417.6C384.6 430.8 360.6 443.8 334.7 451.2C308.9 458.6 280.0 464.5 251.8 462.2C223.6 459.9 191.7 453.0 165.6 "
        "437.3C139.6 421.6 111.7 396.7 95.4 368.0C79.0 339.3 67.5 299.3 67.5 265.0C67.5 230.7 79.0 190.7 95.4 162.0C111.7 "
        "133.3 139.6 108.4 165.6 92.7C191.7 77.0 223.6 70.1 251.8 67.8C280.0 65.5 308.9 71.4 334.7 78.8C360.6 86.2 384.6 "
        "99.2 407.0 112.4C429.3 125.7 449.3 142.1 468.6 158.4C487.9 174.8 505.3 192.8 522.7 210.5C540.1 228.3 556.2 246.8 "
        "573.0 265.0C589.8 283.2 605.9 301.7 623.3 319.5C640.7 337.2 658.1 355.2 677.4 371.6C696.7 387.9 716.7 404.3 739.0 "
        "417.6C761.4 430.8 785.4 443.8 811.3 451.2C837.1 458.6 866.0 464.5 894.2 462.2C922.4 459.9 954.3 453.0 980.4 "
        "437.3C1006.4 421.6 1034.3 396.7 1050.6 368.0C1067.0 339.3 1078.5 299.3 1078.5 265.0C1078.5 230.7 1067.0 190.7 "
        "1050.6 162.0C1034.3 133.3 1006.4 108.4 980.4 92.7C954.3 77.0 922.4 70.1 894.2 67.8C866.0 65.5 837.1 71.4 811.3 "
        "78.8C785.4 86.2 761.4 99.2 739.0 112.4C716.7 125.7 696.7 142.1 677.4 158.4C658.1 174.8 640.7 192.8 623.3 "
        "210.5C605.9 228.3 589.8 246.8 573.0 265.0Z")  # the logo's loop, as on the site
GEAR = ("M19.38 10.17 L21.91 10.67 L21.91 13.33 L19.38 13.83 L18.51 15.92 L19.95 18.07 L18.07 19.95 L15.92 18.51 L13.83 "
        "19.38 L13.33 21.91 L10.67 21.91 L10.17 19.38 L8.08 18.51 L5.93 19.95 L4.05 18.07 L5.49 15.92 L4.62 13.83 L2.09 "
        "13.33 L2.09 10.67 L4.62 10.17 L5.49 8.08 L4.05 5.93 L5.93 4.05 L8.08 5.49 L10.17 4.62 L10.67 2.09 L13.33 2.09 "
        "L13.83 4.62 L15.92 5.49 L18.07 4.05 L19.95 5.93 L18.51 8.08Z")


def render_app(site_dir=None):
    """The app on its own; given the built site's folder, the site's playground: inside the site's own header
    and footer, dressed by its stylesheet, with the model view."""
    if site_dir is None:
        return _fill(ALONE)
    index = (pathlib.Path(site_dir) / "index.html").read_text(encoding="utf-8")
    header = _rooted(_part(index, '<header class="top">', "</header>")) or OWN_HEADER
    return _fill(dict(SITE, HEADER=header, FOOTER=_rooted(_part(index, '<footer class="foot">', "</footer>"))))


def _part(page, start, end):
    i = page.find(start)
    j = page.find(end, i) if i >= 0 else -1
    return page[i:j + len(end)] if j >= 0 else ""


def _rooted(html):
    """The site's own links made absolute, since the playground lives under /app/, and its link marked current."""
    html = html.replace('href="index.html', 'href="/index.html').replace('href="settings.html', 'href="/settings.html')
    return html.replace('class="section-link playground" href="/app/"', 'class="section-link playground" href="/app/" aria-current="page"')


def _fill(parts):
    page = PAGE
    for key, value in parts.items():
        page = page.replace("{{" + key + "}}", value)
    return page


OWN_HEADER = """<header class="top">
  <div class="pane brand">
    <a class="logo" href="/" aria-label="Loopwright"><span class="wm" aria-hidden="true">L<svg class="loop" viewBox="0 0 1152 520" focusable="false"><defs><linearGradient id="loop-gradient" gradientUnits="userSpaceOnUse" x1="10" y1="0" x2="1136" y2="0"><stop offset="0" stop-color="#05F7FF"/><stop offset=".5" stop-color="#01BFFF"/><stop offset="1" stop-color="#004AF0"/></linearGradient></defs><path d="{{LOOP}}" stroke="url(#loop-gradient)" stroke-width="115"/></svg>pwright</span></a>
    <span class="title">Playground</span>
  </div>
</header>""".replace("{{LOOP}}", LOOP)

# On its own the page carries the site's look itself; with the site, styles.css gives it all of this.
BASE_CSS = """:root {
  --paper: #ece6d8; --sheet: #f6f2e9; --panel: #f2ede2; --ink: #23211d; --ink-2: #4a453d; --graphite: #6b665c;
  --rule: #cdc4b2; --line: #3a3631; --lift: rgba(35, 33, 29, 0.14); --blue: #004af0; --red: #d23b2a;
  --sans: "Instrument Sans", "Helvetica Neue", Arial, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, "Cascadia Mono", Consolas, monospace;
  color-scheme: light;
}
* { box-sizing: border-box; }
body {
  margin: 0; color: var(--ink); font: 400 15px/1.5 var(--sans); background-color: var(--paper);
  background-image: linear-gradient(rgba(35, 33, 29, 0.075) 1px, transparent 1px), linear-gradient(90deg, rgba(35, 33, 29, 0.075) 1px, transparent 1px),
    linear-gradient(rgba(35, 33, 29, 0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(35, 33, 29, 0.035) 1px, transparent 1px);
  background-size: 60px 60px, 60px 60px, 12px 12px, 12px 12px; background-position: -1px -1px;
  -webkit-font-smoothing: antialiased;
}
a { color: var(--blue); }
.sr { position: absolute; width: 1px; height: 1px; margin: -1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
.top { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; padding: 14px 16px 0; }
.pane { display: flex; align-items: stretch; height: 44px; border: 1px solid var(--line); background: var(--sheet); box-shadow: 3px 3px 0 var(--lift); }
.pane > * + * { border-left: 1px solid var(--line); }
.logo { display: flex; align-items: center; padding: 0 14px; background: #000; color: #fff; text-decoration: none; }
.wm { display: inline-flex; align-items: center; font: 700 20px/1 "Outfit", var(--sans); letter-spacing: -0.01em; white-space: nowrap; }
.wm .loop { width: 1.152em; height: 0.52em; margin: 0 -0.02em 0 0.01em; }
.loop path { fill: none; stroke-linecap: round; stroke-linejoin: round; }
.title { display: flex; align-items: center; padding: 0 14px; font: 500 13px/1 var(--mono); }
"""

SITE = {
    "HEAD": """<meta name="loopwright:app" content="/app/">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/styles.css">
<link rel="stylesheet" href="/figure.css">
<script>document.documentElement.classList.add("js");</script>
<script src="/model.js" defer></script>
<script src="/main.js" defer></script>""",
    "BASE": "",
    "INTRO": """<section class="section playground-intro" aria-labelledby="playground-title">
  <h1 class="page-title" id="playground-title">Playground</h1>
  <p>Pick a ResPlan plan, upload a drawing or draw rooms on a grid. Loopwright solves it at once, and again after every change you make. Edit and cut on the plan; the model builds the design the way this site's figures are built, with a signal running round each ring.</p>
  <p class="hand" aria-hidden="true">click a cable in the model to cut it</p>
</section>""",
    "VIEWS": """<div class="views" role="group" aria-label="View">
        <button type="button" id="view-plan" aria-pressed="true">Plan</button><button type="button" id="view-model" aria-pressed="false">Model</button>
      </div>""",
    "MODEL": """<figure class="plate-figure" id="model-figure" hidden><div class="plate has-control"></div></figure>
    <p class="sr" aria-live="polite" id="model-live"></p>""",
}
ALONE = {"HEAD": '<link rel="icon" href="data:,">', "BASE": BASE_CSS, "HEADER": OWN_HEADER, "INTRO": "", "VIEWS": "", "MODEL": "",
         "FOOTER": ""}


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Loopwright playground</title>
{{HEAD}}
<style>
{{BASE}}
:root { --ok: #1f7a4a; --glass: #bcd6e5; --hall: #e3dccd; --max: 1480px; }  /* the app needs the room; the intro and footer follow */
[hidden] { display: none !important; }
.playground-intro { padding-top: clamp(36px, 6vw, 72px); }
.playground-intro .hand { margin-top: 10px; }
.strip { max-width: var(--max); margin: 0 auto; padding: 18px var(--gutter, 16px) 0; color: var(--ink-2); font: 500 13px/1.4 var(--mono); min-height: 1.4em; }
.strip b { color: var(--ink); font-weight: 500; }
#app { max-width: var(--max); margin: 0 auto; display: grid; grid-template-columns: 300px minmax(0, 1fr) 340px; gap: 16px; padding: 14px var(--gutter, 16px) 32px; align-items: start; }
@media (max-width: 1200px) { #app { grid-template-columns: minmax(0, 1fr) 320px; } #source { grid-column: 1 / -1; } }
@media (max-width: 760px) { #app { grid-template-columns: minmax(0, 1fr); } }
#app section { min-width: 0; padding: 12px 14px; border: 1px solid var(--line); background: var(--sheet); box-shadow: 3px 3px 0 var(--lift); }
#app aside { display: grid; gap: 14px; min-width: 0; }
#app h2 { margin: 0 0 8px; color: var(--graphite); font: 500 12.5px/1.3 var(--mono); }
#app ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 5px; font-size: 14px; }
#app button, #app select, #app input { font: inherit; color: var(--ink); }
#app button { padding: 6px 10px; border: 1px solid var(--line); background: var(--sheet); font: 500 13px/1 var(--mono); cursor: pointer; box-shadow: 2px 2px 0 var(--lift); }
#app button:hover:not(:disabled) { background: var(--ink); color: var(--sheet); }
#app button[aria-pressed="true"], #app button[aria-selected="true"] { background: var(--ink); color: var(--sheet); }
#app button:disabled { opacity: 0.45; cursor: default; box-shadow: none; }
#app button:focus-visible, #app select:focus-visible, #app input:focus-visible { outline: 2px solid var(--blue); outline-offset: 2px; }
#app #load-id, #app #import, #app #draw-solve { background: var(--blue); border-color: var(--blue); color: #fff; }
#app select, #app input[type=number], #app input[inputmode] { padding: 4px 6px; border: 1px solid var(--line); background: #fbf9f4; font: 400 13px/1.3 var(--mono); }
#app input[type=number], #app input[inputmode] { width: 110px; }
#app label { font-size: 14px; }
#app .tabs, #app .row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 10px; }
#app .pane-body { display: grid; gap: 10px; }
#app .hint { margin: 0; color: var(--graphite); font-size: 13px; }
#stage { display: grid; gap: 10px; min-width: 0; }
#toolbar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
#app .views { display: inline-flex; margin-right: 6px; }
#app .views button { box-shadow: none; }
#app .views button + button { border-left: 0; }
#canvas { border: 1px solid var(--line); background: var(--panel); box-shadow: 3px 3px 0 var(--lift); }
#plan { width: 100%; height: auto; display: block; touch-action: none; }
#plan .room { stroke: var(--ink); stroke-opacity: 0.25; }
#plan .room.flag { stroke: var(--red); stroke-opacity: 1; stroke-width: var(--u2); stroke-dasharray: var(--u4) var(--u2); }
#plan .room.sel { stroke: var(--blue); stroke-opacity: 1; stroke-width: var(--u3); }
#plan .wall { fill: var(--ink); } #plan .door { fill: var(--panel); } #plan .window { fill: var(--glass); stroke: var(--ink-2); }
#plan .door-hit { fill: transparent; stroke: transparent; cursor: pointer; }
#plan.editing .door-hit:hover { stroke: var(--blue); }
#plan.editing .room { cursor: pointer; }
#plan .leg { fill: none; stroke-linejoin: round; stroke-linecap: round; }
#plan .leg-hit { fill: none; stroke: transparent; pointer-events: none; }
#plan.cutting .leg-hit { pointer-events: stroke; cursor: crosshair; }
#plan .nums, #plan.editing .leg, #plan.editing .node, #plan.editing .hub, #plan.cutting .node, #plan.cutting .hub { pointer-events: none; }
#plan .leg.hl { stroke: var(--blue) !important; filter: drop-shadow(0 0 2px var(--blue)); }
#plan .leg.cut { stroke: var(--red) !important; stroke-dasharray: var(--u3) var(--u2); }
#plan .node { fill: #fbf9f4; } #plan .node.rev { stroke-dasharray: var(--u2) var(--u1); }
#plan .lbl { fill: var(--ink); font-family: var(--mono); text-anchor: middle; dominant-baseline: central; pointer-events: none; }
#plan .lbl.halo { paint-order: stroke; stroke: #fbf9f4; stroke-linejoin: round; }
#plan .grid line { stroke: var(--rule); } #plan .grid line.major { stroke: var(--ink-2); stroke-opacity: 0.35; }
#plan .sketch { fill: var(--hall); stroke: var(--ink); } #plan .ghost { fill: none; stroke: var(--blue); stroke-dasharray: .2 .1; }
#rules li { display: grid; grid-template-columns: 70px 44px minmax(0, 1fr); gap: 6px; align-items: baseline; font-size: 13px; }
#app #rules button { padding: 2px 6px; font-size: 12px; box-shadow: none; }
#rules .pass .state { color: var(--ok); } #rules .fail .state { color: var(--red); font-weight: 700; } #rules .skip .state { color: var(--graphite); }
#app .detail { color: var(--graphite); overflow-wrap: anywhere; }
#status { min-height: 1.4em; color: var(--graphite); font: 400 13px/1.4 var(--mono); } #status.err { color: var(--red); font-weight: 500; }
#draw-rooms li, #draw-doors li { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
#model-figure { margin: 0; }
#model-figure .plate { position: relative; padding: 46px 14px 58px; border: 1px solid var(--line); background: var(--panel); box-shadow: 3px 3px 0 var(--lift); overflow: hidden; }
#model-figure .corners > span { position: absolute; color: var(--graphite); font: 500 12.5px/1.25 var(--mono); pointer-events: none; }
#model-figure .corners > [data-corner="fig"] { top: 15px; left: 16px; color: var(--ink); }
#model-figure .corners > [data-corner="title"] { top: 15px; right: 16px; color: var(--ink); }
#model-figure .corners > [data-corner="hint"] { bottom: 19px; left: 140px; }
#model-figure .corners > [data-corner="readout"] { bottom: 19px; right: 16px; color: var(--ink); text-align: right; }
#app .plate-control { position: absolute; left: 16px; bottom: 13px; }
#app .plate-control[aria-pressed="true"] { background: var(--sheet); border-color: var(--red); color: var(--red); }
#model { outline: none; }
#model:focus-visible { outline: 2px solid var(--blue); outline-offset: 6px; }
@media (max-width: 760px) { #model-figure .corners > [data-corner="hint"] { display: none; } }
@media (prefers-reduced-motion: reduce) { #plan .leg { transition: none !important; } }
</style></head>
<body>
{{HEADER}}
{{INTRO}}
<div class="strip"><span id="metrics"></span></div>
<main id="app">
  <section id="source" aria-label="Plan source">
    <div class="tabs" role="tablist">
      <button type="button" role="tab" id="tab-id" aria-controls="pane-id">Plan by id</button>
      <button type="button" role="tab" id="tab-upload" aria-controls="pane-upload">Upload</button>
      <button type="button" role="tab" id="tab-draw" aria-controls="pane-draw">Draw</button>
    </div>
    <div class="pane-body" id="pane-id" role="tabpanel">
      <label>ResPlan plan <input id="plan-id" inputmode="numeric" value="16448"></label>
      <div class="row"><button type="button" id="load-id">Solve</button></div>
      <p class="hint" id="dataset-note"></p>
    </div>
    <div class="pane-body" id="pane-upload" role="tabpanel" hidden>
      <input type="file" id="file" accept=".png,.jpg,.jpeg,.bmp,.webp,.pdf,.dxf" aria-label="Plan file">
      <label>Metres per pixel <input id="m-per-px" type="number" step="any" min="0"></label>
      <label>or flat area, m² <input id="area" type="number" step="any" min="0"></label>
      <label>PDF drawing scale 1: <input id="pdf-scale" type="number" step="any" min="0"></label>
      <div class="row"><button type="button" id="import">Import and solve</button></div>
      <p class="hint">DXF: rooms on a ROOMS layer with a type label inside each, doors on a DOORS layer. Images and PDFs: clean, straight-on drawings; check the room types afterwards.</p>
    </div>
    <div class="pane-body" id="pane-draw" role="tabpanel" hidden>
      <p class="hint">Drag on the grid to add a room (snaps to 0.5 m). Then tick the doors and solve.</p>
      <h2>Rooms</h2><ul id="draw-rooms"></ul>
      <h2>Doors</h2><ul id="draw-doors"></ul>
      <div class="row"><button type="button" id="draw-solve">Solve this sketch</button><button type="button" id="draw-clear">Clear</button></div>
    </div>
  </section>
  <div id="stage">
    <div id="toolbar" role="toolbar" aria-label="Design tools">
      {{VIEWS}}
      <button type="button" id="mode-view" aria-pressed="true">View</button>
      <button type="button" id="mode-edit" aria-pressed="false">Edit</button>
      <button type="button" id="mode-cut" aria-pressed="false">Cut cable</button>
      <label>Zone rule <select id="zone-rule"><option value="strict">strict</option><option value="circulation">circulation</option><option value="through_rooms">through rooms</option></select></label>
      <button type="button" id="undo" disabled>Undo edit</button>
      <button type="button" id="reset" disabled>Reset edits</button>
      <button type="button" id="installer" disabled>Installer pack</button>
      <button type="button" id="download" disabled>Download design</button>
    </div>
    <div id="status" role="status" aria-live="polite"></div>
    <div id="canvas"><svg id="plan" role="img" aria-label="Floor plan with hubs, nodes and cable rings"></svg></div>
    {{MODEL}}
  </div>
  <aside>
    <section><h2>Why this many hubs?</h2><p id="explain" class="hint">Solve a plan to see.</p></section>
    <section id="edit-panel" hidden><h2>Edit</h2>
      <p class="hint">Click a door to remove it. Pick a room to change its type or connect it to a neighbour.</p>
      <div class="row"><label>Room <select id="edit-room"></select></label></div>
      <div class="row"><label>Type <select id="edit-type"><option>living</option><option>bedroom</option><option>kitchen</option><option>storage</option><option>bathroom</option><option>stair</option></select></label><button type="button" id="apply-type">Change type</button></div>
      <div class="row"><label>Connect to <select id="edit-other"></select></label><button type="button" id="apply-connect">Add door</button></div>
    </section>
    <section id="cut-panel" hidden><h2>Cut the cable</h2><p class="hint" id="cut-hint">Click any leg of a ring to cut it.</p><ul id="cut"></ul></section>
    <section><h2>Per-hub summary</h2><ul id="hubs"></ul></section>
    <section><h2>What a reviewer confirms</h2><ul id="reviewer"></ul></section>
    <section><h2>Validator</h2><ul id="rules"></ul></section>
    <section><h2>Diagnostics</h2><ul id="diagnostics"></ul></section>
    <section id="notes-panel" hidden><h2>Import notes</h2><ul id="notes"></ul></section>
  </aside>
</main>
{{FOOTER}}
<script>
(function () {
  "use strict";
  var NS = "http://www.w3.org/2000/svg", RINGS = ["#004AF0", "#23211D", "#8A3FD1"];
  var FILL = { living: "#F29E57", bedroom: "#97DDFF", kitchen: "#BBED7E", storage: "#D79BD6", bathroom: "#84888C", stair: "#CFC8B9" };
  var TYPES = ["living", "bedroom", "kitchen", "storage", "bathroom", "stair"];
  var GRID_W = 20, GRID_H = 14, SNAP = 0.5;
  var state = { source: null, edits: [], settings: { zone_link: "strict" }, data: null, mode: "view", view: "plan",
                tab: "id", cut: null, draw: { rooms: [], doors: {} }, drag: null, model: null };
  var $ = function (id) { return document.getElementById(id); };
  var svg = $("plan");

  function el(tag, attrs, parent) {
    var e = document.createElementNS(NS, tag);
    Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    if (parent) parent.appendChild(e);
    return e;
  }
  function text(tag, value, parent, cls) {
    var e = document.createElement(tag);
    e.textContent = value;
    if (cls) e.className = cls;
    parent.appendChild(e);
    return e;
  }
  function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }
  function status(msg, isError) { var s = $("status"); s.textContent = msg || ""; s.className = isError ? "err" : ""; }
  function pathD(polys) {
    return polys.map(function (rings) {
      return rings.map(function (r) { return "M" + r.map(function (p) { return p.join(","); }).join("L") + "Z"; }).join("");
    }).join("");
  }
  function post(path, body) {
    return fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(function (r) {
        return r.json().then(function (j) { if (!r.ok) throw new Error(j.detail || r.statusText); return j; });
      });
  }

  // ---------- solving ----------
  function request() { return { source: state.source, edits: state.edits, settings: state.settings, model: state.view === "model" }; }
  function solve() {
    if (!state.source) return Promise.resolve();
    status("Solving…");
    return post("/api/solve", request()).then(function (d) {
      state.data = d; state.cut = null;
      render();
      if (state.view === "model") renderModel();
      status("Solved in " + d.design.metrics.runtime_s + " s.");
    }).catch(function (e) {
      if (state.edits.length) state.edits.pop();
      status(e.message, true);
      updateButtons();
    });
  }
  function edit(op) { state.edits.push(op); return solve(); }

  // ---------- drawing the design ----------
  function colourOf(hubs) {
    var c = {};
    hubs.forEach(function (hb, i) {
      if (hubs.length <= RINGS.length) { c[hb.id] = RINGS[i]; return; }
      var living = hb.zone.some(function (r) { return r.indexOf("living") === 0; });
      c[hb.id] = living ? RINGS[0] : (hb.zone.length === 1 ? RINGS[1] : RINGS[2]);
    });
    return function (hub) { return c[hub] || RINGS[0]; };
  }
  function render() {
    var D = state.data, X = D.design;
    clear(svg);
    var b = D.bounds, w = b[2] - b[0], h = b[3] - b[1], pad = Math.max(w, h) * 0.04, u = Math.max(w, h) / 160;
    svg.setAttribute("viewBox", (b[0] - pad) + " " + (b[1] - pad) + " " + (w + 2 * pad) + " " + (h + 2 * pad));
    svg.style.setProperty("--u1", u * 0.6); svg.style.setProperty("--u2", u); svg.style.setProperty("--u3", u * 1.6); svg.style.setProperty("--u4", u * 2.4);
    svg.setAttribute("class", state.mode === "edit" ? "editing" : (state.mode === "cut" ? "cutting" : ""));
    var colour = colourOf(X.hubs), flagged = (D.explain.rooms || []);
    var gRooms = el("g", { id: "layer-rooms" }, svg);
    D.rooms.forEach(function (r) {
      var p = el("path", { d: pathD(r.polys), "data-room": r.id, fill: FILL[r.type] || "var(--hall)", "stroke-width": u * 0.3,
                           "class": "room" + (flagged.indexOf(r.id) >= 0 ? " flag" : "") }, gRooms);
      p.addEventListener("click", function () { if (state.mode === "edit") selectRoom(r.id); });
      var t = el("title", {}, p); t.textContent = r.id + " · " + r.type + " · " + r.area + " m²";
    });
    el("path", { d: pathD(D.walls), "class": "wall" }, svg);
    el("path", { d: pathD(D.windows), "class": "window", "stroke-width": u * 0.3 }, svg);
    var gDoors = el("g", { id: "layer-doors" }, svg);
    D.doors.forEach(function (poly, k) {
      el("path", { d: pathD([poly]), "class": "door" }, gDoors);
      var hit = el("path", { d: pathD([poly]), "class": "door-hit", "data-door": k, "stroke-width": u * 3 }, gDoors);
      hit.addEventListener("click", function () { if (state.mode === "edit") edit({ op: "remove_door", door: k }); });
    });
    var gRings = el("g", { id: "layer-rings" }, svg), gNums = el("g", { "class": "nums" }, svg);
    var cut = state.cut, feed = {};
    if (cut) {
      var info = D.cuts[cut.ring].filter(function (c) { return c.leg === cut.leg; })[0];
      info.fed_forward.forEach(function (f) { feed[f.node] = "fwd"; });
      info.fed_reverse.forEach(function (f) { feed[f.node] = "rev"; });
    }
    X.rings.forEach(function (ring) {
      ring.legs.forEach(function (leg) {
        var isCut = cut && cut.ring === ring.hub && cut.leg === leg.n;
        var pts = leg.path.map(function (p) { return p.join(","); }).join(" ");
        el("polyline", { points: pts, "class": "leg" + (isCut ? " cut" : ""), stroke: colour(ring.hub), "stroke-width": u * 0.9,
                         "data-ring": ring.hub, "data-leg": leg.n }, gRings);
        var hit = el("polyline", { points: pts, "class": "leg-hit", "stroke-width": u * 4,
                                   "data-hit-ring": ring.hub, "data-hit-leg": leg.n }, gRings);
        hit.addEventListener("click", function () { if (state.mode === "cut") cutLeg(ring.hub, leg.n); });
        var best = null, len = -1;
        for (var i = 1; i < leg.path.length; i++) {
          var a = leg.path[i - 1], c = leg.path[i], l = Math.abs(c[0] - a[0]) + Math.abs(c[1] - a[1]);
          if (l > len) { len = l; best = [(a[0] + c[0]) / 2, (a[1] + c[1]) / 2]; }
        }
        if (best && len > 0) {
          if (leg.n === ring.legs.length) el("circle", { cx: best[0], cy: best[1], r: u * 2.6, fill: "none", stroke: colour(ring.hub), "stroke-width": u * 0.4 }, gNums);
          el("circle", { cx: best[0], cy: best[1], r: u * 1.9, "class": "node", stroke: colour(ring.hub), "stroke-width": u * 0.5 }, gNums);
          el("text", { x: best[0], y: best[1], "class": "lbl", "font-size": u * 2.2 }, gNums).textContent = String(leg.n);
        }
      });
    });
    X.nodes.forEach(function (n) {
      el("circle", { cx: n.pos[0], cy: n.pos[1], r: u * 2.8, "class": "node" + (feed[n.id] === "rev" ? " rev" : ""),
                     stroke: colour(n.hub), "stroke-width": u * 0.7, "data-node": n.id }, svg);
      el("text", { x: n.pos[0], y: n.pos[1], "class": "lbl", "font-size": u * 2.2 }, svg).textContent = n.id;
    });
    X.hubs.forEach(function (hb) {
      el("rect", { x: hb.pos[0] - u * 2.4, y: hb.pos[1] - u * 2.4, width: u * 4.8, height: u * 4.8, fill: colour(hb.id),
                   "class": "hub", "data-hub": hb.id }, svg);
      el("text", { x: hb.pos[0] + u * 5, y: hb.pos[1] - u * 3, "class": "lbl halo", "font-size": u * 3,
                   "stroke-width": u * 0.9 }, svg).textContent = hb.id;
    });
    panels();
  }

  // ---------- the model view: the design as the site's scale model (model.js runs its signal) ----------
  function renderModel() {
    var figure = $("model-figure"), M = state.data && state.data.model;
    if (!figure) return;
    if (state.model) { state.model.stop(); state.model = null; }
    var plate = figure.querySelector(".plate");
    clear(plate);
    if (!M) return;
    var X = state.data.design, corners = document.createElement("div");
    corners.className = "corners"; corners.setAttribute("aria-hidden", "true");
    [["fig", "Model"], ["title", "Plan " + X.plan_id + ", " + X.rings.length + (X.rings.length === 1 ? " ring" : " rings")],
     ["hint", "Click a cable to cut it"], ["readout", ""]].forEach(function (c) {
      var span = text("span", c[1], corners);
      span.setAttribute("data-corner", c[0]);
      if (c[0] === "readout") span.setAttribute("data-readout", "");
    });
    plate.appendChild(corners);
    var stage = document.createElement("div");
    stage.className = "stage"; stage.id = "model"; stage.tabIndex = 0; stage.setAttribute("role", "group");
    stage.setAttribute("aria-label", "Scale model of the design. Left and right arrows pick a cable leg, Enter cuts or rejoins it, Escape rejoins every leg.");
    var parsed = new DOMParser().parseFromString(M.svg, "image/svg+xml").documentElement;
    stage.appendChild(document.importNode(parsed, true));
    plate.appendChild(stage);
    var cut = text("button", "Cut a leg", plate, "plate-control");
    cut.type = "button"; cut.setAttribute("aria-pressed", "false"); cut.setAttribute("data-cut", "");
    if (M.rings.length && window.loopwrightModel) state.model = window.loopwrightModel(stage, stage.querySelector("svg"), M.rings);
    else cut.disabled = true;
  }
  function setView(view) {
    if (!$("model-figure")) return;
    state.view = view;
    $("view-plan").setAttribute("aria-pressed", String(view === "plan"));
    $("view-model").setAttribute("aria-pressed", String(view === "model"));
    $("canvas").hidden = view === "model";
    $("model-figure").hidden = view !== "model";
    if (view === "model" && state.mode !== "view") setMode("view");
    if (view === "model" && state.data) {
      if (state.data.model) renderModel(); else solve();
    }
  }

  function panels() {
    var D = state.data, X = D.design, m = X.metrics, metrics = $("metrics");
    clear(metrics);
    [["Hubs", m.hubs + (m.hubs === m.hub_lower_bound ? " (= bound)" : " (bound " + m.hub_lower_bound + ")")],
     ["Cable", m.length_m + " m"], ["Bends", m.bends], ["Crossings", m.crossings], ["J", m.J],
     ["Valid", X.validation.valid ? "yes" : "no"]].forEach(function (p) {
      var s = text("span", p[0] + " ", metrics, "metric"); s.setAttribute("data-metric", p[0].toLowerCase());
      text("b", String(p[1]), s); metrics.appendChild(document.createTextNode("  "));
    });
    $("explain").textContent = D.explain.text;
    var hubs = $("hubs"); clear(hubs);
    X.hubs.forEach(function (hb) {
      var ring = X.rings.filter(function (r) { return r.hub === hb.id; })[0];
      text("li", hb.id + " · " + hb.zone.join(", ") + " · " + hb.area_m2 + " m² | " + hb.nodes + (hb.nodes === 1 ? " node | " : " nodes | ") +
           Number(ring.length_m).toFixed(1) + " m, " + ring.bends + (ring.bends === 1 ? " bend" : " bends"), hubs);
    });
    var rev = $("reviewer"); clear(rev);
    (X.reviewer || []).forEach(function (line) { text("li", line, rev); });
    var rules = $("rules"); clear(rules);
    X.validation.checks.forEach(function (c) {
      var li = document.createElement("li");
      li.className = c.pass === true ? "pass" : (c.pass === false ? "fail" : "skip");
      var btn = text("button", c.id, li); btn.type = "button"; btn.setAttribute("data-rule", c.id);
      btn.addEventListener("click", function () { setView("plan"); highlight(c.where); });
      text("span", c.pass === true ? "pass" : (c.pass === false ? "FAIL" : "skip"), li, "state");
      text("span", c.detail || "", li, "detail");
      rules.appendChild(li);
    });
    var diag = $("diagnostics"); clear(diag);
    (X.diagnostics || []).forEach(function (d) {
      var rest = Object.assign({}, d); delete rest.code;
      text("li", d.code + (Object.keys(rest).length ? " " + JSON.stringify(rest) : ""), diag);
    });
    if (!(X.diagnostics || []).length) text("li", "none", diag);
    var rooms = D.rooms.map(function (r) { return r.id; });
    [$("edit-room"), $("edit-other")].forEach(function (sel) {
      var keep = sel.value; clear(sel);
      rooms.forEach(function (id) { text("option", id, sel).value = id; });
      if (rooms.indexOf(keep) >= 0) sel.value = keep;
    });
    cutPanel();
    updateButtons();
  }

  function highlight(where) {
    Array.prototype.forEach.call(svg.querySelectorAll(".leg.hl"), function (e) { e.classList.remove("hl"); });
    (where || []).forEach(function (wh) {
      var e = svg.querySelector('.leg[data-ring="' + wh.ring + '"][data-leg="' + wh.leg + '"]');
      if (e) e.classList.add("hl");
    });
  }

  // ---------- modes ----------
  function setMode(mode) {
    state.mode = mode;
    ["view", "edit", "cut"].forEach(function (m) { $("mode-" + m).setAttribute("aria-pressed", String(m === mode)); });
    $("edit-panel").hidden = mode !== "edit";
    $("cut-panel").hidden = mode !== "cut";
    if (mode !== "cut") state.cut = null;
    if (mode !== "view" && state.view === "model") setView("plan");
    if (state.data && state.tab !== "draw") render();
  }
  function selectRoom(id) {
    Array.prototype.forEach.call(svg.querySelectorAll(".room.sel"), function (e) { e.classList.remove("sel"); });
    var p = svg.querySelector('.room[data-room="' + id + '"]');
    if (p) p.classList.add("sel");
    $("edit-room").value = id;
    var r = state.data.rooms.filter(function (x) { return x.id === id; })[0];
    if (r) $("edit-type").value = r.type;
  }
  function cutLeg(ring, leg) { state.cut = { ring: ring, leg: leg }; render(); }
  function cutPanel() {
    var list = $("cut"); clear(list);
    if (!state.cut || !state.data) return;
    var c = state.data.cuts[state.cut.ring].filter(function (x) { return x.leg === state.cut.leg; })[0];
    var name = function (f) { return f.node + " (" + f.m + " m)"; };
    text("li", "Cut " + state.cut.ring + " leg " + state.cut.leg + ".", list);
    text("li", "Fed forward: " + (c.fed_forward.map(name).join(", ") || "none"), list);
    text("li", "Fed from the other end: " + (c.fed_reverse.map(name).join(", ") || "none"), list);
    text("li", "Longest feed " + c.farthest_m + " m. No device lost.", list).setAttribute("data-cut-summary", "1");
  }
  function updateButtons() {
    var has = !!state.data;
    $("undo").disabled = !state.edits.length; $("reset").disabled = !state.edits.length;
    $("installer").disabled = !has; $("download").disabled = !has;
  }

  // ---------- sources ----------
  function setTab(tab) {
    state.tab = tab;
    ["id", "upload", "draw"].forEach(function (t) {
      $("tab-" + t).setAttribute("aria-selected", String(t === tab));
      $("pane-" + t).hidden = t !== tab;
    });
    if (tab === "draw") { setView("plan"); drawGrid(); } else if (state.data) render(); else clear(svg);
  }
  function startFrom(source, notes) {
    state.source = source; state.edits = [];
    var panel = $("notes-panel"), list = $("notes"); clear(list);
    (notes || []).forEach(function (n) { text("li", n, list); });
    panel.hidden = !(notes || []).length;
    if (state.tab === "draw") setTab("id");
    return solve();
  }
  function loadById() {
    var id = $("plan-id").value.trim();
    if (!id) return status("Type a plan id.", true);
    return startFrom({ plan_id: /^[0-9]+$/.test(id) ? Number(id) : id });
  }
  function importFile() {
    var f = $("file").files[0];
    if (!f) return status("Choose a PNG, JPEG, PDF or DXF file first.", true);
    var form = new FormData();
    form.append("file", f);
    [["m_per_px", "m-per-px"], ["area_m2", "area"], ["scale", "pdf-scale"]].forEach(function (p) {
      if ($(p[1]).value) form.append(p[0], $(p[1]).value);
    });
    status("Reading " + f.name + "…");
    fetch("/api/import", { method: "POST", body: form }).then(function (r) {
      return r.json().then(function (j) { if (!r.ok) throw new Error(j.detail || r.statusText); return j; });
    }).then(function (sketch) {
      startFrom({ sketch: { rooms: sketch.rooms, doors: sketch.doors, wall_m: sketch.wall_m || 0.1 } }, sketch.notes);
    }).catch(function (e) { status(e.message, true); });
  }

  // ---------- drawing a sketch ----------
  function svgPoint(evt) {
    var pt = svg.createSVGPoint(); pt.x = evt.clientX; pt.y = evt.clientY;
    var p = pt.matrixTransform(svg.getScreenCTM().inverse());
    var snap = function (v, hi) { return Math.min(hi, Math.max(0, Math.round(v / SNAP) * SNAP)); };
    return [snap(p.x, GRID_W), snap(p.y, GRID_H)];
  }
  function rectOf(a, b) { return [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])]; }
  function overlaps(r, s) { return r[0] < s[2] && s[0] < r[2] && r[1] < s[3] && s[1] < r[3]; }
  function adjacent() {
    var R = state.draw.rooms, out = [];
    for (var i = 0; i < R.length; i++) for (var j = i + 1; j < R.length; j++) {
      var a = R[i].rect, b = R[j].rect, shared = 0;
      if (a[2] === b[0] || b[2] === a[0]) shared = Math.min(a[3], b[3]) - Math.max(a[1], b[1]);
      if (a[3] === b[1] || b[3] === a[1]) shared = Math.max(shared, Math.min(a[2], b[2]) - Math.max(a[0], b[0]));
      if (shared >= 1) out.push([i, j]);
    }
    return out;
  }
  function roomLabel(i) { return (i + 1) + ". " + state.draw.rooms[i].type; }
  function drawGrid() {
    clear(svg);
    svg.setAttribute("class", "");
    svg.setAttribute("viewBox", "-0.5 -0.5 " + (GRID_W + 1) + " " + (GRID_H + 1));
    var g = el("g", { "class": "grid" }, svg);
    for (var x = 0; x <= GRID_W; x += SNAP) el("line", { x1: x, y1: 0, x2: x, y2: GRID_H, "class": x % 1 === 0 ? "major" : "", "stroke-width": 0.02 }, g);
    for (var y = 0; y <= GRID_H; y += SNAP) el("line", { x1: 0, y1: y, x2: GRID_W, y2: y, "class": y % 1 === 0 ? "major" : "", "stroke-width": 0.02 }, g);
    state.draw.rooms.forEach(function (r, i) {
      var q = r.rect;
      el("rect", { x: q[0], y: q[1], width: q[2] - q[0], height: q[3] - q[1], "class": "sketch", fill: FILL[r.type],
                   "stroke-width": 0.06, "data-sketch-room": i }, svg);
      el("text", { x: (q[0] + q[2]) / 2, y: (q[1] + q[3]) / 2, "class": "lbl", "font-size": 0.45 }, svg).textContent = roomLabel(i);
    });
    var ghost = el("rect", { "class": "ghost", "stroke-width": 0.06, visibility: "hidden" }, svg);
    svg.onpointerdown = function (evt) {
      if (state.tab !== "draw") return;
      state.drag = svgPoint(evt); svg.setPointerCapture(evt.pointerId);
    };
    svg.onpointermove = function (evt) {
      if (state.tab !== "draw" || !state.drag) return;
      var q = rectOf(state.drag, svgPoint(evt));
      ghost.setAttribute("x", q[0]); ghost.setAttribute("y", q[1]); ghost.setAttribute("width", q[2] - q[0]);
      ghost.setAttribute("height", q[3] - q[1]); ghost.setAttribute("visibility", "visible");
    };
    svg.onpointerup = function (evt) {
      if (state.tab !== "draw" || !state.drag) return;
      var q = rectOf(state.drag, svgPoint(evt)); state.drag = null;
      if (q[2] - q[0] < 1 || q[3] - q[1] < 1) { drawGrid(); return status("Rooms must be at least 1 m by 1 m.", true); }
      if (state.draw.rooms.some(function (r) { return overlaps(r.rect, q); })) { drawGrid(); return status("Rooms can't overlap.", true); }
      state.draw.rooms.push({ rect: q, type: state.draw.rooms.length ? "bedroom" : "living" });
      status(""); drawLists(); drawGrid();
    };
    drawLists();
  }
  function drawLists() {
    var list = $("draw-rooms"); clear(list);
    state.draw.rooms.forEach(function (r, i) {
      var li = document.createElement("li"), q = r.rect;
      text("span", (i + 1) + ".", li);
      var sel = document.createElement("select"); sel.setAttribute("aria-label", "Type of room " + (i + 1));
      TYPES.forEach(function (t) { text("option", t, sel).value = t; }); sel.value = r.type;
      sel.addEventListener("change", function () { r.type = sel.value; drawLists(); drawGrid(); });
      li.appendChild(sel);
      text("span", ((q[2] - q[0]) * (q[3] - q[1])).toFixed(1) + " m²", li, "hint");
      var del = text("button", "Remove", li); del.type = "button";
      del.addEventListener("click", function () { state.draw.rooms.splice(i, 1); state.draw.doors = {}; drawLists(); drawGrid(); });
      list.appendChild(li);
    });
    var doors = $("draw-doors"); clear(doors);
    var pairs = adjacent();
    if (!pairs.length) text("li", state.draw.rooms.length > 1 ? "No rooms share a wall yet." : "Draw two neighbouring rooms.", doors, "hint");
    pairs.forEach(function (p) {
      var key = p.join("-"), li = document.createElement("li"), box = document.createElement("input");
      box.type = "checkbox"; box.id = "door-" + key; box.checked = !!state.draw.doors[key];
      box.addEventListener("change", function () { state.draw.doors[key] = box.checked; });
      var lab = document.createElement("label"); lab.htmlFor = box.id; lab.textContent = roomLabel(p[0]) + " ↔ " + roomLabel(p[1]);
      li.appendChild(box); li.appendChild(lab); doors.appendChild(li);
    });
  }
  function solveSketch() {
    if (!state.draw.rooms.length) return status("Draw at least one room.", true);
    var rooms = state.draw.rooms.map(function (r) {
      var q = r.rect;
      return { type: r.type, polygon: [[q[0], q[1]], [q[2], q[1]], [q[2], q[3]], [q[0], q[3]]] };
    });
    var doors = adjacent().filter(function (p) { return state.draw.doors[p.join("-")]; });
    startFrom({ sketch: { rooms: rooms, doors: doors } });
  }

  // ---------- outputs ----------
  function openInstaller() {
    var win = window.open("", "_blank");
    fetch("/api/installer", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(request()) })
      .then(function (r) { if (!r.ok) throw new Error("installer pack failed"); return r.text(); })
      .then(function (html) { if (win) { win.document.open(); win.document.write(html); win.document.close(); } })
      .catch(function (e) { if (win) win.close(); status(e.message, true); });
  }
  function download() {
    var X = state.data.design, a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(X, null, 1)], { type: "application/json" }));
    a.download = "loopwright-" + String(X.plan_id).replace(/[^A-Za-z0-9_-]/g, "_") + ".json";
    document.body.appendChild(a); a.click(); a.remove();
  }

  // ---------- links: #edit, #cut, #installer, #draw and #upload (or #dxf) open the app in that mode ----------
  function openFromLink(available) {
    var want = location.hash.slice(1);
    if (want === "draw" || want === "upload" || want === "dxf") return setTab(want === "draw" ? "draw" : "upload");
    if (["edit", "cut", "installer"].indexOf(want) < 0) return;
    if (want !== "installer") setMode(want);
    if (!available) return;
    var loading = loadById();
    if (want === "installer" && loading) loading.then(function () { $("installer").focus(); });
  }

  // ---------- wiring ----------
  $("tab-id").addEventListener("click", function () { setTab("id"); });
  $("tab-upload").addEventListener("click", function () { setTab("upload"); });
  $("tab-draw").addEventListener("click", function () { setTab("draw"); });
  $("load-id").addEventListener("click", loadById);
  $("plan-id").addEventListener("keydown", function (e) { if (e.key === "Enter") loadById(); });
  $("import").addEventListener("click", importFile);
  $("draw-solve").addEventListener("click", solveSketch);
  $("draw-clear").addEventListener("click", function () { state.draw = { rooms: [], doors: {} }; drawGrid(); });
  ["view", "edit", "cut"].forEach(function (m) { $("mode-" + m).addEventListener("click", function () { setMode(m); }); });
  if ($("view-plan")) {
    $("view-plan").addEventListener("click", function () { setView("plan"); });
    $("view-model").addEventListener("click", function () { setView("model"); });
  }
  $("zone-rule").addEventListener("change", function () { state.settings.zone_link = $("zone-rule").value; solve(); });
  $("undo").addEventListener("click", function () { state.edits.pop(); solve(); });
  $("reset").addEventListener("click", function () { state.edits = []; solve(); });
  $("apply-type").addEventListener("click", function () { edit({ op: "set_type", room: $("edit-room").value, to: $("edit-type").value }); });
  $("apply-connect").addEventListener("click", function () {
    var a = $("edit-room").value, b = $("edit-other").value;
    if (a === b) return status("Pick two different rooms to connect.", true);
    edit({ op: "connect", rooms: [a, b] });
  });
  $("edit-room").addEventListener("change", function () { selectRoom($("edit-room").value); });
  $("installer").addEventListener("click", openInstaller);
  $("download").addEventListener("click", download);

  fetch("/api/plans").then(function (r) { return r.json(); }).then(function (p) {
    if (p.available) {
      $("dataset-note").textContent = p.test.length + " test-split plans available, for example " + p.test.slice(0, 3).join(", ") + ".";
      setTab("id");
      if ($("model-figure") && !location.hash) { setView("model"); loadById(); }  // the playground opens on a solved plan, as a model
    } else {
      $("dataset-note").textContent = "ResPlan isn't on this machine; draw or upload a plan instead.";
      $("load-id").disabled = true;
      setTab("draw");
    }
    openFromLink(p.available);
  }).catch(function () { setTab("draw"); openFromLink(false); });
})();
</script>
</body></html>
"""
