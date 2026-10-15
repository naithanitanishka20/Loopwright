"""The pipeline: plan dict in, schema loopwright/2 dict out."""
import time

from shapely.geometry import Point

from loopwright import SCHEMA
from loopwright.config import DEFAULT
from loopwright.geometry.nodes import place_nodes
from loopwright.geometry.walkable import piece_index, pieces, walkable_hub, walkable_node, walkable_region
from loopwright.geometry.portals import connector_ids, door_graph, is_connected
from loopwright.geometry.spaces import build_model
from loopwright.optimize.baseline import greedy_zones
from loopwright.optimize.zones import feasible_zones, lower_bound, members, min_hubs
from loopwright.routing.grid import INF, GridRouter, best_cycle, best_ring_order
from loopwright.routing.straight import l_leg
from loopwright.validate.rules import validate
from loopwright.validate.score import leg_length_and_bends, reviewer_lines, ring_metrics, score


def _zones(model, settings, diagnostics, piece_of):
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
        rooms = [ids[k] for k in members(mask, n)]
        # One ring needs one walkable area: rooms the door graph links but a wall
        # or external area separates can't share a hub.
        if len({piece_of.get(r) for r in rooms}) != 1 or piece_of.get(rooms[0]) is None:
            return False
        return is_connected(rooms, adj, connectors)

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


def _hub_on_ring(router, zone, model):
    """Put the hub on the cheapest tour through the zone's nodes, inside one of the zone's rooms.

    A hub on the path between two consecutive nodes adds no cable; on a corner of
    that path it also removes the bend there, since turns at the hub don't count.
    Returns (rooms in ring order, hub position, hub room, leg paths), or None when
    no point of the tour lies inside the zone's rooms.
    """
    order, cost = best_cycle(router, zone)
    if cost == INF:
        return None
    m = len(order)
    paths = [router.path(order[j], order[(j + 1) % m]) for j in range(m)]
    rooms = [(r, model.space(r).geom) for r in zone]
    best = None
    for k, path in enumerate(paths):
        ends = (Point(path[0]), Point(path[-1]))
        for x, y, seg, corner in router.vertices_on(path):
            pt = Point(x, y)
            room = next((r for r, g in rooms if g.covers(pt)), None)
            if room is None:
                continue
            key = (corner, round(min(pt.distance(e) for e in ends), 6))
            if best is None or key > best[0]:
                best = (key, k, seg, (x, y), corner, room)
    if best is None:
        return None
    _, k, seg, at, corner, room = best
    pts = [tuple(p) for p in paths[k]]
    if corner:
        first, second = pts[:seg + 2], pts[seg + 1:]
    else:
        first, second = pts[:seg + 1] + [at], [at] + pts[seg + 1:]
    start = (k + 1) % m
    ring_rooms = [order[(start + t) % m] for t in range(m)]
    legs = [second] + [paths[(start + t) % m] for t in range(m - 1)] + [first]
    return ring_rooms, at, room, [[list(p) for p in leg] for leg in legs]


def solve(plan, settings=DEFAULT):
    t0 = time.perf_counter()
    model = build_model(plan, settings)
    s = model.m_per_unit
    diagnostics = list(model.diagnostics)
    nodes_at = place_nodes(model, settings)
    region = walkable_region(model)
    parts = pieces(region)
    for sp in model.eligible:
        if piece_index(nodes_at[sp.id], parts) is None:
            moved = walkable_node(sp.geom, region, s)
            if moved is not None:
                nodes_at[sp.id] = moved
                diagnostics.append({"code": "NODE_MOVED", "room": sp.id, "reason": "pole of inaccessibility is not walkable"})
            else:
                diagnostics.append({"code": "ROOM_NOT_WALKABLE", "room": sp.id})
    piece_of = {rid: piece_index(pos, parts) for rid, pos in nodes_at.items()}
    elig = model.eligible
    total_area = sum(sp.area_m2 for sp in elig)
    n = len(elig)
    lb = lower_bound(total_area, n, settings)
    zones, hub_minimum, adj = _zones(model, settings, diagnostics, piece_of)
    _explain_extra_hubs(model, zones, adj, lb, diagnostics)

    hub_pos = {}
    for zi, zone in enumerate(zones, start=1):
        main_room = max(zone, key=lambda r: model.space(r).area_m2)
        hub_pos[f"H{zi}"] = (main_room, walkable_hub(model.space(main_room).geom, nodes_at[main_room], region, s))
    stops = {**{rid: pos for rid, pos in nodes_at.items()}, **{h: pos for h, (_, pos) in hub_pos.items()}}
    router = GridRouter(model, stops, settings)

    counter = 1
    hubs, nodes, rings = [], [], []
    fallback = None
    for zi, zone in enumerate(zones, start=1):
        hub_id = f"H{zi}"
        main_room, hpos = hub_pos[hub_id]
        zrouter = router
        stops_here = [hub_id] + zone
        if any(router.cost(a, b) == INF for a in stops_here for b in stops_here if a != b):
            # Narrow doors can close under the clearance; retry this zone on a finer grid without it.
            if fallback is None:
                fallback = GridRouter(model, stops, settings.with_overrides(clearance_m=0.0), spacing_m=0.1)
            zrouter = fallback
            diagnostics.append({"code": "ROUTER_FALLBACK", "ring": hub_id})
        on_ring = _hub_on_ring(zrouter, zone, model) if len(zone) >= 2 else None
        if on_ring is not None:
            order, hpos, main_room, leg_paths = on_ring
        else:
            order, _ = best_ring_order(zrouter, hub_id, zone)
            leg_paths = None
        hubs.append({"id": hub_id, "pos": list(hpos), "room": main_room, "zone": zone,
                     "area_m2": round(sum(model.space(r).area_m2 for r in zone), 1), "nodes": len(zone)})
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
            if leg_paths is not None:
                path = leg_paths[i - 1]
            else:
                path = zrouter.path(a, b) if zrouter.cost(a, b) < INF else None
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
    greedy = greedy_zones([sp.id for sp in elig], [sp.area_m2 for sp in elig], adj, settings)
    out["metrics"] = {"hubs": len(hubs), "hub_lower_bound": lb, "hub_minimum": hub_minimum if hub_minimum < 10 ** 9 else None,
                      "hubs_greedy": len(greedy), **metrics, "runtime_s": None}
    out["ranking_key"] = [len(hubs), metrics["J"]]
    out["validation"] = validate(plan, out, settings)
    out["reviewer"] = reviewer_lines(out, out["validation"], lb, total_area, n)
    out["diagnostics"] = diagnostics
    out["metrics"]["runtime_s"] = round(time.perf_counter() - t0, 3)
    return out, model
