"""Viewer v1: one self-contained HTML page per plan, plus an index page.

No server and no external files: the plan geometry and the design are embedded
as JSON. The JSON is escaped so plan text can't close the <script> tag, and the
page only ever writes data with textContent, never innerHTML.
"""
import json
from html import escape

from loopwright.geometry.heal import flat
from loopwright.output.schema import safe_stem


def _polys(geom):
    out = []
    for p in flat(geom):
        if p.geom_type == "Polygon":
            rings = [p.exterior, *p.interiors]
            out.append([[[round(x, 2), round(y, 2)] for x, y in r.coords] for r in rings])
    return out


def viewer_data(model, out):
    zone_of = {r: h["id"] for h in out["hubs"] for r in h["zone"]}
    return {
        "bounds": [round(v, 2) for v in model.layers["inner"].bounds],
        "rooms": [{"id": sp.id, "type": sp.type, "area": round(sp.area_m2, 1), "eligible": sp.eligible,
                   "hub": zone_of.get(sp.id), "polys": _polys(sp.geom)} for sp in model.spaces],
        "walls": _polys(model.layers.get("wall")),
        "doors": _polys(model.layers.get("door")),
        "windows": _polys(model.layers.get("window")),
        "design": out,
    }


def _embed(obj):
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def render_viewer(model, out):
    return (TEMPLATE.replace("__TITLE__", escape(f"Loopwright · plan {out['plan_id']}"))
            .replace("__DATA__", _embed(viewer_data(model, out))))


def render_index(designs):
    """Render the landing page for written design documents."""
    rows = []
    for design in sorted(designs, key=lambda design: str(design["plan_id"])):
        metrics = design["metrics"]
        plan_id = escape(str(design["plan_id"]))
        href = escape(safe_stem(design["plan_id"]), quote=True)
        state = "valid" if design["validation"]["valid"] else "invalid"
        hubs, bound, length, bends, cost = (escape(str(metrics[key]), quote=True)
                                            for key in ("hubs", "hub_lower_bound", "length_m", "bends", "J"))
        rows.append(f'<tr><td><a href="{href}.html">{plan_id}</a></td><td>{hubs}</td><td>{bound}</td>'
                    f'<td>{length}</td><td>{bends}</td><td>{cost}</td><td class="{state}">{state}</td></tr>')
    return INDEX.replace("__ROWS__", "\n".join(rows)).replace("__COUNT__", str(len(rows)))


STYLE = """
:root { --paper:#F4F6F5; --sheet:#FFFFFF; --ink:#18202B; --ink2:#4B5664; --rule:#D3D9D7; --grey:#E6EAE8;
        --ok:#2B7A4B; --bad:#B0261D; --hl:#C21F2E; color-scheme: light; }
@media (prefers-color-scheme: dark) { :root { --paper:#0F141A; --sheet:#151C24; --ink:#E3E8EC; --ink2:#A2ADB9;
        --rule:#2A3440; --grey:#1D2630; --ok:#5CC28A; --bad:#FF6B60; --hl:#FF5C5C; color-scheme: dark; } }
* { box-sizing: border-box; }
body { margin: 0; background: var(--paper); color: var(--ink); font: 14px/1.5 system-ui, "Segoe UI", sans-serif; }
header { padding: 12px 20px; border-bottom: 1px solid var(--rule); display: flex; flex-wrap: wrap; gap: 6px 22px; align-items: baseline; }
h1 { font-size: 20px; margin: 0; }
.metric b { font-family: ui-monospace, Consolas, monospace; }
table { border-collapse: collapse; }
th, td { padding: 6px 10px; border-bottom: 1px solid var(--rule); text-align: left; }
.valid { color: var(--ok); } .invalid { color: var(--bad); }
"""

TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>""" + STYLE + """
main { display: grid; grid-template-columns: minmax(0, 1fr) 360px; gap: 16px; padding: 16px 20px; }
@media (max-width: 900px) { main { grid-template-columns: minmax(0, 1fr); } }
#canvas { background: var(--sheet); border: 1px solid var(--rule); align-self: start; }
svg { width: 100%; height: auto; display: block; }
aside { display: grid; gap: 14px; align-content: start; min-width: 0; }
section { background: var(--sheet); border: 1px solid var(--rule); padding: 10px 12px; }
h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .06em; color: var(--ink2); margin: 0 0 6px; }
ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; }
label { margin-right: 10px; white-space: nowrap; }
#rules button { font: 600 12px ui-monospace, Consolas, monospace; border: 1px solid var(--rule); background: var(--paper); color: var(--ink); padding: 1px 6px; cursor: pointer; }
#rules li { display: grid; grid-template-columns: 52px 46px minmax(0, 1fr); gap: 6px; align-items: baseline; font-size: 12px; }
#rules .pass .state { color: var(--ok); } #rules .fail .state { color: var(--bad); font-weight: 700; } #rules .skip .state { color: var(--ink2); }
.detail { color: var(--ink2); overflow-wrap: anywhere; }
.room { stroke: none; } .wall { fill: var(--ink); } .door { fill: var(--sheet); } .window { fill: var(--sheet); stroke: var(--ink2); }
.leg { fill: none; stroke-linejoin: round; stroke-linecap: round; }
.leg.hl { stroke: var(--hl) !important; filter: drop-shadow(0 0 2px var(--hl)); }
.node { fill: var(--sheet); } .lbl { fill: var(--ink); font-family: ui-monospace, Consolas, monospace; text-anchor: middle; dominant-baseline: central; }
button.play { font: inherit; padding: 2px 10px; cursor: pointer; }
@media (prefers-reduced-motion: reduce) { .leg { transition: none !important; } }
</style></head>
<body>
<header><h1 id="title"></h1><span id="metrics"></span></header>
<main>
  <div id="canvas"><svg id="plan" role="img" aria-label="Floor plan with hubs, nodes and cable rings"></svg></div>
  <aside>
    <section><h2>Layers</h2><div id="toggles"></div></section>
    <section><h2>Rings</h2><select id="ring-pick"></select> <button class="play" id="play" type="button">Play</button></section>
    <section><h2>Per-hub summary</h2><ul id="hubs"></ul></section>
    <section><h2>What a reviewer confirms</h2><ul id="reviewer"></ul></section>
    <section><h2>Validator</h2><ul id="rules"></ul></section>
    <section><h2>Diagnostics</h2><ul id="diagnostics"></ul></section>
  </aside>
</main>
<script id="data" type="application/json">__DATA__</script>
<script>
(function () {
  "use strict";
  var D = JSON.parse(document.getElementById("data").textContent);
  var X = D.design, NS = "http://www.w3.org/2000/svg";
  var COLOURS = ["#2A78D6", "#EB6834", "#1BAF7A"];
  var svg = document.getElementById("plan");
  var b = D.bounds, w = b[2] - b[0], h = b[3] - b[1], pad = Math.max(w, h) * 0.04, u = Math.max(w, h) / 160;
  svg.setAttribute("viewBox", (b[0] - pad) + " " + (b[1] - pad) + " " + (w + 2 * pad) + " " + (h + 2 * pad));
  function el(tag, attrs, parent) {
    var e = document.createElementNS(NS, tag);
    Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    parent.appendChild(e);
    return e;
  }
  function text(tag, value, parent, cls) {
    var e = document.createElement(tag);
    e.textContent = value;
    if (cls) e.className = cls;
    parent.appendChild(e);
    return e;
  }
  function pathD(polys) {
    return polys.map(function (rings) {
      return rings.map(function (r) { return "M" + r.map(function (p) { return p.join(","); }).join("L") + "Z"; }).join("");
    }).join("");
  }
  // Up to three zones: one colour each. More than three can't stay distinguishable,
  // so colour by role (living-room zone, one-room zones, the rest) and rely on labels.
  var hubColour = {};
  X.hubs.forEach(function (hb, i) {
    if (X.hubs.length <= COLOURS.length) { hubColour[hb.id] = COLOURS[i]; return; }
    var living = hb.zone.some(function (r) { return r.indexOf("living") === 0; });
    hubColour[hb.id] = living ? COLOURS[0] : (hb.zone.length === 1 ? COLOURS[1] : COLOURS[2]);
  });
  function colour(hub) { return hubColour[hub] || COLOURS[0]; }
  var layers = {};
  function layer(name) { var g = el("g", { id: "layer-" + name }, svg); layers[name] = g; return g; }

  var gRooms = layer("rooms");
  D.rooms.forEach(function (r) {
    el("path", { d: pathD(r.polys), "class": "room", "data-room": r.id,
                 fill: r.hub ? colour(r.hub) : "var(--grey)", "fill-opacity": r.hub ? 0.22 : 1 }, gRooms);
  });
  el("path", { d: pathD(D.walls), "class": "wall" }, layer("walls"));
  el("path", { d: pathD(D.windows), "class": "window", "stroke-width": u * 0.3 }, layer("windows"));
  el("path", { d: pathD(D.doors), "class": "door" }, layer("doors"));

  var gRings = layer("rings"), gNums = layer("numbers"), legEls = {};
  X.rings.forEach(function (ring) {
    ring.legs.forEach(function (leg) {
      var pts = leg.path.map(function (p) { return p.join(","); }).join(" ");
      var line = el("polyline", { points: pts, "class": "leg", stroke: colour(ring.hub), "stroke-width": u * 0.9,
                                  "data-ring": ring.hub, "data-leg": leg.n }, gRings);
      legEls[ring.hub + ":" + leg.n] = line;
      var best = null, len = -1;
      for (var i = 1; i < leg.path.length; i++) {
        var a = leg.path[i - 1], c = leg.path[i], l = Math.abs(c[0] - a[0]) + Math.abs(c[1] - a[1]);
        if (l > len) { len = l; best = [(a[0] + c[0]) / 2, (a[1] + c[1]) / 2]; }
      }
      if (best) {
        if (leg.n === ring.legs.length) el("circle", { cx: best[0], cy: best[1], r: u * 2.6, fill: "none", stroke: colour(ring.hub), "stroke-width": u * 0.4 }, gNums);
        el("circle", { cx: best[0], cy: best[1], r: u * 1.9, "class": "node", stroke: colour(ring.hub), "stroke-width": u * 0.5 }, gNums);
        el("text", { x: best[0], y: best[1], "class": "lbl", "font-size": u * 2.2 }, gNums).textContent = String(leg.n);
      }
    });
  });
  var gNodes = layer("nodes");
  X.nodes.forEach(function (n) {
    el("circle", { cx: n.pos[0], cy: n.pos[1], r: u * 2.8, "class": "node", stroke: colour(n.hub), "stroke-width": u * 0.7 }, gNodes);
    el("text", { x: n.pos[0], y: n.pos[1], "class": "lbl", "font-size": u * 2.2 }, gNodes).textContent = n.id;
  });
  var gHubs = layer("hubs");
  X.hubs.forEach(function (hb) {
    el("rect", { x: hb.pos[0] - u * 2.4, y: hb.pos[1] - u * 2.4, width: u * 4.8, height: u * 4.8, fill: colour(hb.id) }, gHubs);
    el("text", { x: hb.pos[0] + u * 5, y: hb.pos[1], "class": "lbl", "font-size": u * 3 }, gHubs).textContent = hb.id;
  });

  var toggles = document.getElementById("toggles");
  Object.keys(layers).forEach(function (name) {
    var lab = document.createElement("label"), box = document.createElement("input");
    box.type = "checkbox"; box.checked = true; box.id = "toggle-" + name;
    box.addEventListener("change", function () { layers[name].style.display = box.checked ? "" : "none"; });
    lab.appendChild(box); lab.appendChild(document.createTextNode(" " + name)); toggles.appendChild(lab);
  });

  document.getElementById("title").textContent = "Plan " + X.plan_id;
  var m = X.metrics, metrics = document.getElementById("metrics");
  [["Hubs", m.hubs + " (bound " + m.hub_lower_bound + ")"], ["Cable", m.length_m + " m"], ["Bends", m.bends],
   ["J", m.J], ["Valid", X.validation.valid ? "yes" : "no"], ["Zone rule", X.rules.zone_link]].forEach(function (p) {
    var s = text("span", p[0] + " ", metrics, "metric"); text("b", String(p[1]), s); metrics.appendChild(document.createTextNode("  "));
  });

  var hubsList = document.getElementById("hubs");
  X.hubs.forEach(function (hb) {
    var ring = X.rings.filter(function (r) { return r.hub === hb.id; })[0];
    text("li", hb.id + " · " + hb.zone.join(", ") + " · " + hb.area_m2 + " m² | " + hb.nodes + " nodes | " +
         Number(ring.length_m).toFixed(1) + " m, " + ring.bends + " bends", hubsList);
  });
  var rev = document.getElementById("reviewer");
  (X.reviewer || []).forEach(function (line) { text("li", line, rev); });

  var rules = document.getElementById("rules");
  function highlight(where) {
    Object.keys(legEls).forEach(function (k) { legEls[k].classList.remove("hl"); });
    (where || []).forEach(function (wh) { var e = legEls[wh.ring + ":" + wh.leg]; if (e) e.classList.add("hl"); });
  }
  X.validation.checks.forEach(function (c) {
    var li = document.createElement("li");
    li.className = c.pass === true ? "pass" : (c.pass === false ? "fail" : "skip");
    var btn = document.createElement("button");
    btn.type = "button"; btn.textContent = c.id; btn.setAttribute("data-rule", c.id);
    btn.addEventListener("click", function () { highlight(c.where); });
    li.appendChild(btn);
    text("span", c.pass === true ? "pass" : (c.pass === false ? "FAIL" : "skip"), li, "state");
    text("span", c.detail || "", li, "detail");
    rules.appendChild(li);
  });
  var diag = document.getElementById("diagnostics");
  (X.diagnostics || []).forEach(function (d) {
    var rest = Object.assign({}, d); delete rest.code;
    text("li", d.code + (Object.keys(rest).length ? " " + JSON.stringify(rest) : ""), diag);
  });
  if (!(X.diagnostics || []).length) text("li", "none", diag);

  var pick = document.getElementById("ring-pick");
  text("option", "all rings", pick).value = "";
  X.hubs.forEach(function (hb) { text("option", hb.id, pick).value = hb.id; });
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  document.getElementById("play").addEventListener("click", function () {
    var want = pick.value, delay = 0;
    X.rings.forEach(function (ring) {
      if (want && ring.hub !== want) return;
      ring.legs.forEach(function (leg) {
        var e = legEls[ring.hub + ":" + leg.n], total = e.getTotalLength ? e.getTotalLength() : 0;
        if (reduce || !total) return;
        e.style.transition = "none"; e.style.strokeDasharray = total; e.style.strokeDashoffset = total;
        setTimeout(function () { e.style.transition = "stroke-dashoffset 600ms linear"; e.style.strokeDashoffset = 0; }, delay);
        delay += 650;
      });
    });
  });
})();
</script>
</body></html>
"""

INDEX = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Loopwright results</title><style>""" + STYLE + """
main { padding: 16px 20px; } td:nth-child(n+2) { font-family: ui-monospace, Consolas, monospace; }
</style></head><body>
<header><h1>Loopwright results</h1><span>__COUNT__ plans</span></header>
<main><table><thead><tr><th>Plan</th><th>Hubs</th><th>Bound</th><th>Cable (m)</th><th>Bends</th><th>J</th><th>Status</th></tr></thead>
<tbody>
__ROWS__
</tbody></table></main></body></html>
"""
