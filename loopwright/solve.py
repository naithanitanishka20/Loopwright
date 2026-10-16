"""The pipeline: plan dict in, schema loopwright/2 dict out."""
import time

from loopwright import SCHEMA
from loopwright.config import DEFAULT
from loopwright.geometry.nodes import hub_point, place_nodes
from loopwright.geometry.portals import connector_ids, door_graph, is_connected
from loopwright.geometry.spaces import build_model
from loopwright.optimize.zones import feasible_zones, lower_bound, members, min_hubs
from loopwright.routing.grid import INF, GridRouter, best_ring_order
from loopwright.routing.straight import l_leg
from loopwright.validate.rules import validate
from loopwright.validate.score import leg_length_and_bends, reviewer_lines, ring_metrics, score


def _zones(model, settings, diagnostics):
    elig = model.eligible
    ids = [sp.id for sp in elig]
    areas = [sp.area_m2 for sp in elig]
    n = len(ids)
    spaces, adj = door_graph(model)
    connectors = connector_ids(spaces, settings.zone_link)
    for rid in ids:
        if not adj.get(rid):
            diagnostics.append({"code": "NO_LINK", "room": rid})

    def connected(mask):
        return is_connected([ids[k] for k in members(mask, n)], adj, connectors)

    feasible = feasible_zones(areas, settings, connected=connected)
    count, masks = min_hubs(n, feasible)
    zones = [[ids[k] for k in members(m, n)] for m in masks]
    zones.sort(key=lambda z: -sum(model.space(r).area_m2 for r in z))
    return zones, count, adj


def _explain_extra_hubs(model, zones, adj, lb, diagnostics):
    if len(zones) <= lb:
        return
    zone_of = {r: i for i, z in enumerate(zones) for r in z}
    for z in zones:
        if len(z) != 1:
            continue
        room = z[0]
        links = sorted(r for r in adj.get(room, ()) if r in zone_of)
        if not links:
            reason = "no door or opening to another eligible room"
        else:
            full = [f"{r} (zone {sum(model.space(x).area_m2 for x in zones[zone_of[r]]):.1f} m², "
                    f"{len(zones[zone_of[r]])} nodes)" for r in links]
            reason = "joins only through " + "; ".join(full)
        diagnostics.append({"code": "EXTRA_HUB", "room": room, "reason": reason})


def solve(plan, settings=DEFAULT):
    t0 = time.perf_counter()
    model = build_model(plan, settings)
    s = model.m_per_unit
    diagnostics = list(model.diagnostics)
    nodes_at = place_nodes(model, settings)
    elig = model.eligible
    total_area = sum(sp.area_m2 for sp in elig)
    n = len(elig)
    lb = lower_bound(total_area, n, settings)
    zones, hub_minimum, adj = _zones(model, settings, diagnostics)
    _explain_extra_hubs(model, zones, adj, lb, diagnostics)

    hub_pos = {}
    for zi, zone in enumerate(zones, start=1):
        main_room = max(zone, key=lambda r: model.space(r).area_m2)
        hub_pos[f"H{zi}"] = (main_room, hub_point(model.space(main_room).geom, nodes_at[main_room], s))
    stops = {**{rid: pos for rid, pos in nodes_at.items()}, **{h: pos for h, (_, pos) in hub_pos.items()}}
    router = GridRouter(model, stops, settings)

    counter = 1
    hubs, nodes, rings = [], [], []
    for zi, zone in enumerate(zones, start=1):
        hub_id = f"H{zi}"
        main_room, hpos = hub_pos[hub_id]
        hubs.append({"id": hub_id, "pos": list(hpos), "room": main_room, "zone": zone,
                     "area_m2": round(sum(model.space(r).area_m2 for r in zone), 1), "nodes": len(zone)})
        order, cost = best_ring_order(router, hub_id, zone)
        sequence, names = [hub_id], [hub_id]
        for pos_in_ring, room in enumerate(order, start=1):
            nid = f"N{counter}"
            counter += 1
            nodes.append({"id": nid, "room": room, "pos": list(nodes_at[room]), "hub": hub_id, "order": pos_in_ring})
            sequence.append(nid)
            names.append(room)
        sequence.append(hub_id)
        names.append(hub_id)
        legs = []
        for i, (a, b) in enumerate(zip(names, names[1:]), start=1):
            path = router.path(a, b) if router.cost(a, b) < INF else None
            if path is None:
                path = [list(p) for p in l_leg(stops[a], stops[b])]
                diagnostics.append({"code": "ROUTE_UNREACHABLE", "ring": hub_id, "leg": i, "from": a, "to": b})
            length, bends, _, _ = leg_length_and_bends([tuple(p) for p in path])
            legs.append({"n": i, "from": sequence[i - 1], "to": sequence[i], "path": path,
                         "portals": [], "length_m": round(length * s, 2), "bends": bends})
        ring = {"hub": hub_id, "sequence": sequence, "legs": legs}
        ring_len, ring_bends = ring_metrics(ring, s, settings.bend_at_node)
        ring["length_m"], ring["bends"] = round(ring_len, 2), ring_bends
        rings.append(ring)

    out = {
        "schema": SCHEMA,
        "plan_id": plan.get("id"),
        "frame": {"units": "input", "m_per_unit": round(s, 6)},
        "rules": {"max_area_m2": settings.max_area_m2, "max_nodes": settings.max_nodes,
                  "zone_link": settings.zone_link, "axis_aligned": True},
        "weights": {"bend_m": settings.bend_m, "crossing_m": settings.crossing_m, "overlap_factor": settings.overlap_factor},
        "rooms": [{"id": sp.id, "type": sp.type, "area_m2": round(sp.area_m2, 1), "eligible": sp.eligible} for sp in model.spaces],
        "hubs": hubs,
        "nodes": nodes,
        "rings": rings,
    }
    metrics = score(out, settings)
    out["metrics"] = {"hubs": len(hubs), "hub_lower_bound": lb, "hub_minimum": hub_minimum if hub_minimum < 10 ** 9 else None,
                      **metrics, "runtime_s": None}
    out["ranking_key"] = [len(hubs), metrics["J"]]
    out["validation"] = validate(plan, out, settings)
    out["reviewer"] = reviewer_lines(out, out["validation"], lb, total_area, n)
    out["diagnostics"] = diagnostics
    out["metrics"]["runtime_s"] = round(time.perf_counter() - t0, 3)
    return out, model
