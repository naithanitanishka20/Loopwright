"""Why can't a leg be routed? Usage: python scripts/diagnose_unreachable.py 11160"""
import sys

from shapely.ops import unary_union

from loopwright.config import DEFAULT
from loopwright.geometry.heal import flat
from loopwright.geometry.nodes import place_nodes
from loopwright.geometry.spaces import build_model
from loopwright.io.resplan import get_plan, load_plans

plan = get_plan(load_plans("data/ResPlan.zip"), sys.argv[1])
model = build_model(plan, DEFAULT)
walls, doors = model.layers["wall"], model.layers["door"]
print("m_per_unit", round(model.m_per_unit, 4), "wall_depth", plan.get("wall_depth"))
for i, d in enumerate(flat(doors)):
    rect = d.minimum_rotated_rectangle
    xs = [p[0] for p in rect.exterior.coords]
    ys = [p[1] for p in rect.exterior.coords]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    # How much wall remains across the door's short axis if we only remove the door itself?
    across = d.buffer(model.wall_depth * 0.75).intersection(walls.difference(d))
    print(f"door {i}: {w:.1f} x {h:.1f} units, wall left within 0.75 wall depth: {across.area:.1f} units²")
nodes = place_nodes(model, DEFAULT)
region = model.layers["inner"].difference(unary_union([g for g in (walls.difference(doors) if doors is not None else walls,
                                                                    model.layers.get("window")) if g is not None]))
pieces = sorted(flat(region), key=lambda p: -p.area)
print("walkable pieces:", len(pieces), [round(p.area * model.m_per_unit ** 2, 1) for p in pieces[:6]], "m²")
from shapely.geometry import Point
for rid, pos in nodes.items():
    which = next((k for k, p in enumerate(pieces) if p.buffer(1e-6).contains(Point(pos))), None)
    print(f"  node {rid} in walkable piece {which}")
