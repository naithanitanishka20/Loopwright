import time

from loopwright import SCHEMA
from loopwright.config import DEFAULT
from loopwright.geometry.nodes import hub_point, place_nodes
from loopwright.geometry.spaces import build_model
from loopwright.optimize.zones import feasible_zones, lower_bound, members, min_hubs
from loopwright.routing.straight import l_leg, nearest_order
from loopwright.validate.rules import validate
from loopwright.validate.score import leg_length_and_bends, reviewer_lines, ring_metrics, score


def solve(plan, settings=DEFAULT):
    t0 = time.perf_counter()
    model = build_model(plan, settings)
    s = model.m_per_unit
    nodes_at = place_nodes(model, settings)
    elig = model.eligible
    ids = [sp.id for sp in elig]
    areas = [sp.area_m2 for sp in elig]
    n = len(ids)
    total_area = sum(areas)
    lb = lower_bound(total_area, n, settings)

    # Phase 2 does not have a door graph.
    feasible = feasible_zones(areas, settings, connected=None)
    _, masks = min_hubs(n, feasible)
    zones = [[ids[k] for k in members(m, n)] for m in masks]
    zones.sort(key=lambda z: -sum(model.space(r).area_m2 for r in z))
    diagnostics = list(model.diagnostics)
    diagnostics.append({"code": "ZONE_LINK_NOT_CHECKED", "detail": "Phase 2 groups rooms by area and node count only"})

    node_ids = {}
    counter = 1
    hubs, nodes, rings = [], [], []
    for zi, zone in enumerate(zones, start=1):
        hub_id = f"H{zi}"
        main_room = max(zone, key=lambda r: model.space(r).area_m2)
        hpos = hub_point(model.space(main_room).geom, nodes_at[main_room], s)
        hubs.append({"id": hub_id, "pos": list(hpos), "room": main_room, "zone": zone,
                     "area_m2": round(sum(model.space(r).area_m2 for r in zone), 1), "nodes": len(zone)})
        order = nearest_order(hpos, {r: nodes_at[r] for r in zone})
        sequence = [hub_id]
        for pos_in_ring, room in enumerate(order, start=1):
            nid = f"N{counter}"
            counter += 1
            node_ids[room] = nid
            nodes.append({"id": nid, "room": room, "pos": list(nodes_at[room]), "hub": hub_id, "order": pos_in_ring})
            sequence.append(nid)
        sequence.append(hub_id)
        stops = [hpos] + [nodes_at[r] for r in order] + [hpos]
        legs = []
        for i, (a, b) in enumerate(zip(stops, stops[1:]), start=1):
            path = l_leg(a, b)
            length, bends, _, _ = leg_length_and_bends(path)
            legs.append({"n": i, "from": sequence[i - 1], "to": sequence[i], "path": [list(p) for p in path],
                         "portals": [], "length_m": round(length * s, 2), "bends": bends})
        ring = {"hub": hub_id, "sequence": sequence, "legs": legs}
        ring_len, ring_bends = ring_metrics(ring, s, settings.bend_at_node)
        ring["length_m"], ring["bends"] = round(ring_len, 2), ring_bends
        rings.append(ring)

    out = {
        "schema": SCHEMA,
        "plan_id": plan.get("id"),
        "frame": {"units": "input", "m_per_unit": round(s, 6)},
        "rules": {"max_area_m2": settings.max_area_m2, "max_nodes": settings.max_nodes, "zone_link": "none", "axis_aligned": True},
        "weights": {"bend_m": settings.bend_m, "crossing_m": settings.crossing_m, "overlap_factor": settings.overlap_factor},
        "rooms": [{"id": sp.id, "type": sp.type, "area_m2": round(sp.area_m2, 1), "eligible": sp.eligible} for sp in model.spaces],
        "hubs": hubs,
        "nodes": nodes,
        "rings": rings,
    }
    metrics = score(out, settings)
    out["metrics"] = {"hubs": len(hubs), "hub_lower_bound": lb, "hub_minimum": None, **metrics,
                      "runtime_s": None}
    out["ranking_key"] = [len(hubs), metrics["J"]]
    out["validation"] = validate(plan, out, settings)
    out["reviewer"] = reviewer_lines(out, out["validation"], lb, total_area, n)
    out["diagnostics"] = diagnostics
    out["metrics"]["runtime_s"] = round(time.perf_counter() - t0, 3)
    return out, model
