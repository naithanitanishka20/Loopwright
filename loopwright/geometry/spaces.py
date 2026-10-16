"""Turn a raw plan dict into spaces with metre areas.

Room ids are <type>_<k>, where k counts that type's polygon parts (at least the
sliver size) in input order. All living pieces merge into living_0 unless
settings.living_pieces == "split" (assumptions Q9).
"""
import math
from dataclasses import dataclass, field

from shapely.ops import unary_union

from loopwright.config import DEFAULT
from loopwright.geometry.heal import polygons, valid
from loopwright.geometry.nodes import room_pole

ELIGIBLE_TYPES = ("living", "kitchen", "bedroom", "storage")
OTHER_TYPES = ("bathroom", "stair")
LAYERS = ("wall", "door", "window", "balcony", "front_door", "garden", "pool", "parking")


@dataclass
class Space:
    id: str
    type: str
    geom: object
    area_m2: float
    eligible: bool


@dataclass
class PlanModel:
    plan_id: object
    m_per_unit: float
    spaces: list
    layers: dict
    diagnostics: list = field(default_factory=list)
    wall_depth: float = 0.0

    @property
    def eligible(self):
        return [s for s in self.spaces if s.eligible]

    def space(self, space_id):
        return next(s for s in self.spaces if s.id == space_id)


def scale(plan, inner):
    explicit = plan.get("m_per_unit")
    if explicit is not None:
        if isinstance(explicit, bool) or not isinstance(explicit, (int, float)) or not math.isfinite(explicit) or explicit <= 0:
            raise ValueError("plan 'm_per_unit' must be a finite number greater than zero")
        return float(explicit)
    area = plan.get("area")
    if isinstance(area, bool) or not isinstance(area, (int, float)) or not math.isfinite(area) or area <= 0:
        raise ValueError("plan 'area' must be a finite number greater than zero")
    if not math.isfinite(inner.area) or inner.area <= 0:
        raise ValueError("plan 'inner' must have positive finite area")
    return math.sqrt(area / inner.area)


def _wall_depth(plan, m_per_unit):
    value = plan.get("wall_depth")
    if value is None:
        return 0.2 / m_per_unit
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError("plan 'wall_depth' must be a finite number greater than zero")
    return float(value)


def build_model(plan, settings=DEFAULT):
    inner = valid(plan.get("inner"))
    if inner is None or inner.is_empty:
        raise ValueError("plan has no 'inner' boundary")
    s = scale(plan, inner)
    s2 = s * s
    sliver = settings.sliver_m2 / s2
    diagnostics = []
    repaired = sum(1 for k in ELIGIBLE_TYPES + OTHER_TYPES + LAYERS
                   if plan.get(k) is not None and not plan[k].is_empty and not plan[k].is_valid)
    if repaired:
        diagnostics.append({"code": "REPAIRED_GEOMETRY", "layers": repaired})

    spaces = []
    living = polygons(plan.get("living"), sliver)
    if living and settings.living_pieces == "merge":
        geom = unary_union(living)
        spaces.append(Space("living_0", "living", geom, geom.area * s2, True))
    else:
        for i, p in enumerate(living):
            spaces.append(Space(f"living_{i}", "living", p, p.area * s2, True))
    for t in ("kitchen", "bedroom", "storage") + OTHER_TYPES:
        for i, p in enumerate(polygons(plan.get(t), sliver)):
            spaces.append(Space(f"{t}_{i}", t, p, p.area * s2, t in ELIGIBLE_TYPES))

    # Eval-01 meeting: a node keeps node_wall_m from its walls, and very small rooms are left
    # out. A room under min_room_m2, or with no point that far from its walls, gets no node.
    for sp in spaces:
        if not sp.eligible:
            continue
        if sp.area_m2 < settings.min_room_m2:
            reason = f"{sp.area_m2:.1f} m², under the {settings.min_room_m2:g} m² minimum"
        else:
            clearance = room_pole(sp.geom, s)[1]
            if clearance >= settings.node_wall_m:
                continue
            reason = f"no point {settings.node_wall_m:g} m from its walls (at most {clearance:.2f} m)"
        sp.eligible = False
        diagnostics.append({"code": "ROOM_NEGLECTED", "room": sp.id, "reason": reason})
    for sp in spaces:
        if sp.eligible and sp.area_m2 > settings.max_area_m2 + 1e-9:
            diagnostics.append({"code": "ROOM_OVER_CAP", "room": sp.id, "area_m2": round(sp.area_m2, 1)})
    if not any(sp.eligible for sp in spaces):
        diagnostics.append({"code": "NO_ELIGIBLE_ROOM"})

    layers = {k: valid(plan.get(k)) for k in LAYERS}
    wall_depth = _wall_depth(plan, s)
    # Some ResPlan plans have an `inner` outline that leaves out parts of rooms.
    # Rooms are inside the building by definition, so widen the outline to cover
    # every room and door (grown by half a wall to close the passages between
    # them). Walls and external areas are still subtracted later. Assumptions Q16.
    if spaces:
        rooms = unary_union([sp.geom for sp in spaces])
        outside_m2 = rooms.difference(inner).area * s2
        if outside_m2 > 0.5:
            cover = [rooms] + ([layers["door"]] if layers["door"] is not None and not layers["door"].is_empty else [])
            inner = unary_union([inner, unary_union(cover).buffer(0.5 * wall_depth)])
            diagnostics.append({"code": "INNER_REPAIRED", "added_m2": round(outside_m2, 1)})
    layers["inner"] = inner
    return PlanModel(plan.get("id"), s, spaces, layers, diagnostics, wall_depth)
