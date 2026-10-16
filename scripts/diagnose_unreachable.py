"""Why do some plans fail? For each plan: walkable pieces, which piece each room's
node sits in, and the door-graph links that join rooms in different pieces.

Usage: python scripts/diagnose_unreachable.py 407696 742848 ...
"""
import sys

from shapely.geometry import Point
from shapely.ops import unary_union

from loopwright.config import DEFAULT
from loopwright.geometry.heal import flat
from loopwright.geometry.nodes import place_nodes
from loopwright.geometry.portals import door_graph
from loopwright.geometry.spaces import build_model
from loopwright.io.resplan import get_plan, load_plans

plans = load_plans(__import__("os").environ.get("LOOPWRIGHT_DATA", "data/ResPlan.zip"))
for pid in sys.argv[1:]:
    plan = get_plan(plans, pid)
    model = build_model(plan, DEFAULT)
    s2 = model.m_per_unit ** 2
    walls, doors = model.layers["wall"], model.layers["door"]
    blocked = [walls.difference(doors) if doors is not None and not doors.is_empty else walls]
    blocked += [model.layers[k] for k in ("window", "balcony", "garden", "pool", "parking")
                if model.layers.get(k) is not None and not model.layers[k].is_empty]
    region = model.layers["inner"].difference(unary_union(blocked))
    pieces = sorted(flat(region), key=lambda p: -p.area)
    nodes = place_nodes(model, DEFAULT)
    piece_of = {}
    for rid, pos in nodes.items():
        piece_of[rid] = next((k for k, p in enumerate(pieces) if p.buffer(1e-6).contains(Point(pos))), None)
    spaces, adj = door_graph(model)
    bad_links = sorted({tuple(sorted((a, b))) for a in nodes for b in adj.get(a, ()) if b in nodes and piece_of[a] != piece_of[b]})
    print(f"plan {pid}: pieces {[round(p.area * s2, 1) for p in pieces[:5]]} m²; nodes by piece {piece_of}")
    print(f"  links across pieces: {bad_links}")
    print(f"  rooms: {[(sp.id, round(sp.area_m2, 1)) for sp in model.eligible]}")
