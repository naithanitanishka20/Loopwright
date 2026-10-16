"""The demo app served by loopwright serve: one page, no external files, talking only to the local API.

Sources: a ResPlan plan by id, an uploaded image, PDF or DXF, or rooms drawn on
a grid. Every change (door removed, rooms connected, room type changed, zone
rule switched) is re-solved by the server, so the drawing, the validator and
the explanation always describe the same design. Text from the server is only
ever written with textContent.
"""
from loopwright.output.viewer import STYLE


def render_app():
    return PAGE


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Loopwright</title><link rel="icon" href="data:,">
<style>""" + STYLE + """
[hidden] { display: none !important; }
main { display: grid; grid-template-columns: 300px minmax(0, 1fr) 340px; gap: 14px; padding: 14px 16px; align-items: start; }
@media (max-width: 1200px) { main { grid-template-columns: minmax(0, 1fr) 320px; } #source { grid-column: 1 / -1; } }
@media (max-width: 760px) { main { grid-template-columns: minmax(0, 1fr); } }
section, .panel { background: var(--sheet); border: 1px solid var(--rule); padding: 10px 12px; min-width: 0; }
aside { display: grid; gap: 12px; min-width: 0; }
h2 { font-size: 12px; text-transform: uppercase; letter-spacing: .06em; color: var(--ink2); margin: 0 0 6px; }
ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; }
button, select, input { font: inherit; color: var(--ink); }
button { background: var(--paper); border: 1px solid var(--rule); padding: 3px 10px; cursor: pointer; }
button[aria-pressed="true"], button[aria-selected="true"] { background: var(--ink); color: var(--sheet); border-color: var(--ink); }
button:disabled { opacity: .5; cursor: default; }
button:focus-visible, select:focus-visible, input:focus-visible { outline: 2px solid var(--hl); outline-offset: 1px; }
input[type=number], input[inputmode] { width: 110px; padding: 2px 6px; background: var(--sheet); border: 1px solid var(--rule); }
.tabs, .row { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin-bottom: 8px; }
.pane { display: grid; gap: 8px; }
.hint { color: var(--ink2); font-size: 12px; margin: 0; }
#stage { display: grid; gap: 8px; min-width: 0; }
#toolbar { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
#canvas { background: var(--sheet); border: 1px solid var(--rule); }
svg { width: 100%; height: auto; display: block; touch-action: none; }
.room { stroke: none; } .room.flag { stroke: var(--bad); stroke-width: var(--u2); stroke-dasharray: var(--u4) var(--u2); }
.room.sel { stroke: var(--hl); stroke-width: var(--u3); }
.wall { fill: var(--ink); } .door { fill: var(--sheet); } .window { fill: var(--sheet); stroke: var(--ink2); }
.door-hit { fill: transparent; stroke: transparent; cursor: pointer; }
.editing .door-hit:hover { stroke: var(--hl); }
.editing .room { cursor: pointer; }
.leg { fill: none; stroke-linejoin: round; stroke-linecap: round; }
.leg-hit { fill: none; stroke: transparent; pointer-events: none; }
.cutting .leg-hit { pointer-events: stroke; cursor: crosshair; }
.nums, .editing .leg, .editing .node, .editing .hub, .cutting .node, .cutting .hub { pointer-events: none; }
.leg.hl { stroke: var(--hl) !important; filter: drop-shadow(0 0 2px var(--hl)); }
.leg.cut { stroke: var(--bad) !important; stroke-dasharray: var(--u3) var(--u2); }
.node { fill: var(--sheet); } .node.rev { stroke-dasharray: var(--u2) var(--u1); }
.lbl { fill: var(--ink); font-family: ui-monospace, Consolas, monospace; text-anchor: middle; dominant-baseline: central; pointer-events: none; }
.lbl.halo { paint-order: stroke; stroke: var(--sheet); stroke-linejoin: round; }
.grid line { stroke: var(--rule); } .grid line.major { stroke: var(--ink2); stroke-opacity: .35; }
.sketch { fill: var(--grey); stroke: var(--ink); } .ghost { fill: none; stroke: var(--hl); stroke-dasharray: .2 .1; }
#rules li { display: grid; grid-template-columns: 70px 40px minmax(0, 1fr); gap: 6px; align-items: baseline; font-size: 12px; }
#rules button { font: 600 12px ui-monospace, Consolas, monospace; padding: 1px 6px; }
#rules .pass .state { color: var(--ok); } #rules .fail .state { color: var(--bad); font-weight: 700; } #rules .skip .state { color: var(--ink2); }
.detail { color: var(--ink2); overflow-wrap: anywhere; }
#status { min-height: 1.4em; color: var(--ink2); } #status.err { color: var(--bad); font-weight: 600; }
#draw-rooms li, #draw-doors li { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
@media (prefers-reduced-motion: reduce) { .leg { transition: none !important; } }
</style></head>
<body>
<header><h1>Loopwright</h1><span id="metrics"></span></header>
<main id="app">
  <section id="source" aria-label="Plan source">
    <div class="tabs" role="tablist">
      <button type="button" role="tab" id="tab-id" aria-controls="pane-id">Plan by id</button>
      <button type="button" role="tab" id="tab-upload" aria-controls="pane-upload">Upload</button>
      <button type="button" role="tab" id="tab-draw" aria-controls="pane-draw">Draw</button>
    </div>
    <div class="pane" id="pane-id" role="tabpanel">
      <label>ResPlan plan <input id="plan-id" inputmode="numeric" value="16448"></label>
      <div class="row"><button type="button" id="load-id">Solve</button></div>
      <p class="hint" id="dataset-note"></p>
    </div>
    <div class="pane" id="pane-upload" role="tabpanel" hidden>
      <input type="file" id="file" accept=".png,.jpg,.jpeg,.bmp,.webp,.pdf,.dxf" aria-label="Plan file">
      <label>Metres per pixel <input id="m-per-px" type="number" step="any" min="0"></label>
      <label>or flat area, m² <input id="area" type="number" step="any" min="0"></label>
      <label>PDF drawing scale 1: <input id="pdf-scale" type="number" step="any" min="0"></label>
      <div class="row"><button type="button" id="import">Import and solve</button></div>
      <p class="hint">DXF: rooms on a ROOMS layer with a type label inside each, doors on a DOORS layer. Images and PDFs: clean, straight-on drawings; check the room types afterwards.</p>
    </div>
    <div class="pane" id="pane-draw" role="tabpanel" hidden>
      <p class="hint">Drag on the grid to add a room (snaps to 0.5 m). Then tick the doors and solve.</p>
      <h2>Rooms</h2><ul id="draw-rooms"></ul>
      <h2>Doors</h2><ul id="draw-doors"></ul>
      <div class="row"><button type="button" id="draw-solve">Solve this sketch</button><button type="button" id="draw-clear">Clear</button></div>
    </div>
  </section>
  <div id="stage">
    <div id="toolbar" role="toolbar" aria-label="Design tools">
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
<script>
(function () {
  "use strict";
  var NS = "http://www.w3.org/2000/svg", COLOURS = ["#2A78D6", "#EB6834", "#1BAF7A"];
  var TYPES = ["living", "bedroom", "kitchen", "storage", "bathroom", "stair"];
  var GRID_W = 20, GRID_H = 14, SNAP = 0.5;
  var state = { source: null, edits: [], settings: { zone_link: "strict" }, data: null, mode: "view",
                tab: "id", cut: null, draw: { rooms: [], doors: {} }, drag: null };
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
  function request() { return { source: state.source, edits: state.edits, settings: state.settings }; }
  function solve() {
    if (!state.source) return Promise.resolve();
    status("Solving…");
    return post("/api/solve", request()).then(function (d) {
      state.data = d; state.cut = null;
      render();
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
      if (hubs.length <= COLOURS.length) { c[hb.id] = COLOURS[i]; return; }
      var living = hb.zone.some(function (r) { return r.indexOf("living") === 0; });
      c[hb.id] = living ? COLOURS[0] : (hb.zone.length === 1 ? COLOURS[1] : COLOURS[2]);
    });
    return function (hub) { return c[hub] || COLOURS[0]; };
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
      var p = el("path", { d: pathD(r.polys), "data-room": r.id, fill: r.hub ? colour(r.hub) : "var(--grey)",
                           "fill-opacity": r.hub ? 0.22 : 1, "class": "room" + (flagged.indexOf(r.id) >= 0 ? " flag" : "") }, gRooms);
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
      btn.addEventListener("click", function () { highlight(c.where); });
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
    if (tab === "draw") drawGrid(); else if (state.data) render(); else clear(svg);
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
      el("rect", { x: q[0], y: q[1], width: q[2] - q[0], height: q[3] - q[1], "class": "sketch", "stroke-width": 0.06, "data-sketch-room": i }, svg);
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
