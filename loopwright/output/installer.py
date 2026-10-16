"""Installer pack: cable schedule, commissioning sheet, loop resistance and bill of materials.

On an addressable loop the panel numbers devices in the order the cable visits
them, so the ring order is the address order. Loop resistance counts both
conductors over the ring's length; 12.1 ohm/km is the maximum for 1.5 mm²
plain copper at 20 °C (IEC 60228, class 1). Check it against the cable and
panel actually used before relying on it.
"""
import csv
import io
import json
from html import escape

from shapely.geometry import LineString

from loopwright.output.overlay import render_svg
from loopwright.output.resilience import cut_analysis

OHM_PER_KM = 12.1
SLACK = 0.10


def _doors_passed(ring, doors):
    count = 0
    for leg in ring["legs"]:
        if len(leg.get("path") or []) < 2:
            continue
        line = LineString(leg["path"])
        count += sum(1 for d in doors if line.intersects(d))
    return count


def installer_data(design, doors=(), *, slack=SLACK, ohm_per_km=OHM_PER_KM):
    room_of = {n["id"]: n["room"] for n in design["nodes"]}
    hub_room = {h["id"]: h["room"] for h in design["hubs"]}
    cuts = cut_analysis(design)
    rings = []
    for ring in design["rings"]:
        length = ring["length_m"]
        rings.append({
            "hub": ring["hub"],
            "hub_room": hub_room.get(ring["hub"]),
            "addresses": [{"address": i, "node": nid, "room": room_of[nid]}
                          for i, nid in enumerate(ring["sequence"][1:-1], start=1)],
            "length_m": length,
            "bends": ring.get("bends"),
            "doors_passed": _doors_passed(ring, doors),
            "cable_m": round(length * (1 + slack), 1),
            "loop_ohm": round(2 * length * ohm_per_km / 1000, 3),
            "worst_feed_m": max((c["farthest_m"] for c in cuts[ring["hub"]]), default=0.0),
        })
    total = sum(r["length_m"] for r in rings)
    bom = {"hubs": len(rings), "devices": sum(len(r["addresses"]) for r in rings),
           "cable_m": round(total, 1), "cable_m_with_slack": round(total * (1 + slack), 1),
           "max_loop_ohm": max((r["loop_ohm"] for r in rings), default=0.0)}
    return {"plan_id": design.get("plan_id"), "slack": slack, "ohm_per_km": ohm_per_km, "rings": rings, "bom": bom}


def installer_csv(data):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["hub", "address", "node", "room", "ring_cable_m", "ring_loop_ohm"])
    for r in data["rings"]:
        for a in r["addresses"]:
            w.writerow([r["hub"], a["address"], a["node"], a["room"], r["cable_m"], r["loop_ohm"]])
    return buf.getvalue()


CSS = """
:root { --ink:#18202B; --ink2:#4B5664; --line:#D5DBD8; --sheet:#FFFFFF; --wash:#F4F6F5; }
* { box-sizing: border-box; }
body { margin: 0; padding: 24px 16px; font: 14px/1.45 system-ui, sans-serif; color: var(--ink); background: var(--wash); }
main { max-width: 960px; margin: 0 auto; background: var(--sheet); padding: 24px; border: 1px solid var(--line); }
h1 { font-size: 20px; margin: 0 0 4px; } h2 { font-size: 15px; margin: 24px 0 8px; }
.sub { color: var(--ink2); margin: 0 0 16px; }
table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 4px 8px; border-bottom: 1px solid var(--line); }
td.n, th.n { text-align: right; }
.drawing svg { width: 100%; height: auto; border: 1px solid var(--line); }
.cost { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
.cost input { width: 90px; font: inherit; padding: 2px 6px; }
.note { color: var(--ink2); font-size: 12px; }
@media print { body { background: none; padding: 0; } main { border: none; } .cost { display: none; } }
"""


def render_installer(model, design, doors=(), **kw):
    data = installer_data(design, doors, **kw)
    bom = data["bom"]
    rows = "".join(
        f"<tr><td>{escape(r['hub'])}</td><td>{escape(str(r['hub_room']))}</td><td class='n'>{len(r['addresses'])}</td>"
        f"<td class='n'>{r['length_m']}</td><td class='n'>{r['cable_m']}</td><td class='n'>{r['bends']}</td>"
        f"<td class='n'>{r['doors_passed']}</td><td class='n'>{r['loop_ohm']}</td><td class='n'>{r['worst_feed_m']}</td></tr>"
        for r in data["rings"])
    sheet = "".join(
        f"<tr><td>{escape(r['hub'])}</td><td class='n'>{a['address']}</td><td>{escape(a['node'])}</td><td>{escape(a['room'])}</td></tr>"
        for r in data["rings"] for a in r["addresses"])
    title = f"Installer pack · plan {escape(str(data['plan_id']))}"
    payload = json.dumps({"cable_m": bom["cable_m_with_slack"], "hubs": bom["hubs"]})
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title><style>{CSS}</style></head>
<body><main>
<h1>{title}</h1>
<p class="sub">{bom['hubs']} hubs · {bom['devices']} devices · {bom['cable_m']} m of cable ({bom['cable_m_with_slack']} m with {round(data['slack'] * 100)}% slack)</p>
<div class="drawing">{render_svg(model, design)}</div>
<h2>Cable schedule</h2>
<table id="schedule"><thead><tr><th>Hub</th><th>Hub room</th><th class="n">Devices</th><th class="n">Ring m</th><th class="n">Cable m</th>
<th class="n">Bends</th><th class="n">Doors passed</th><th class="n">Loop Ω</th><th class="n">Worst feed m</th></tr></thead><tbody>{rows}</tbody></table>
<p class="note">Loop Ω: both conductors, {data['ohm_per_km']} Ω/km (1.5 mm² copper, IEC 60228). Worst feed: the longest cable run to a device after any single cut.</p>
<h2>Bill of materials</h2>
<table id="bom"><tbody>
<tr><td>Hubs</td><td class="n">{bom['hubs']}</td></tr>
<tr><td>Devices</td><td class="n">{bom['devices']}</td></tr>
<tr><td>Cable, with slack</td><td class="n">{bom['cable_m_with_slack']} m</td></tr>
<tr><td>Highest loop resistance</td><td class="n">{bom['max_loop_ohm']} Ω</td></tr>
</tbody></table>
<div class="cost"><label>Cable ₹/m <input id="rate" type="number" min="0" step="1" value="0"></label>
<label>Per hub ₹ <input id="hubprice" type="number" min="0" step="100" value="0"></label>
<strong>Estimate: ₹<span id="total">0</span></strong></div>
<h2>Commissioning sheet</h2>
<table id="addresses"><thead><tr><th>Hub</th><th class="n">Address</th><th>Device</th><th>Room</th></tr></thead><tbody>{sheet}</tbody></table>
<p class="note">Addresses follow the order the cable visits each device.</p>
</main>
<script>
const D = {payload};
const rate = document.getElementById("rate"), hub = document.getElementById("hubprice"), total = document.getElementById("total");
function update() {{
  const r = Math.max(0, Number(rate.value) || 0), h = Math.max(0, Number(hub.value) || 0);
  total.textContent = Math.round(D.cable_m * r + D.hubs * h).toLocaleString("en-IN");
}}
rate.addEventListener("input", update); hub.addEventListener("input", update); update();
</script>
</body></html>
"""
