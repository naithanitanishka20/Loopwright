"""Import a DXF drawn in Loopwright's layer convention, as rooms and door pairs for io.sketch.

The convention, which any CAD tool can follow:

- ROOMS: one closed polyline per room; neighbouring outlines share their common
  edge. A TEXT or MTEXT on ROOMS inside each outline names the room's type:
  living, bedroom, kitchen, storage, bathroom or stair. Aliases and numbering
  ("Bedroom 2", "WC", "Lounge") are fine.
- DOORS: a line or polyline across the shared edge where two rooms connect.
- Units come from the drawing's $INSUNITS (inches, feet, mm, cm or m); a
  unitless drawing is read as metres unless `m_per_unit` is given.

Architects' own drawings use their own layers, so they need these three layers
added before import.
"""
import re

import ezdxf
from shapely.geometry import LineString, Point, Polygon

from loopwright.geometry.heal import valid
from loopwright.io.organiser import ALIASES
from loopwright.io.sketch import ROOM_TYPES

UNIT_M = {1: 0.0254, 2: 0.3048, 4: 0.001, 5: 0.01, 6: 1.0}


def _room_type(text):
    for word in re.sub(r"[^a-z_]+", " ", text.lower()).split():
        if ALIASES.get(word) in ROOM_TYPES:
            return ALIASES[word]
    return None


def _points(entity, s):
    if entity.dxftype() == "LINE":
        return [(entity.dxf.start.x * s, entity.dxf.start.y * s), (entity.dxf.end.x * s, entity.dxf.end.y * s)]
    if entity.dxftype() == "LWPOLYLINE":
        return [(p[0] * s, p[1] * s) for p in entity.get_points()]
    return [(v.dxf.location.x * s, v.dxf.location.y * s) for v in entity.vertices]


def read_dxf(path, *, m_per_unit=None):
    """{"rooms": [{"type", "polygon"}], "doors": [[i, j]]} in metres."""
    doc = ezdxf.readfile(str(path))
    s = m_per_unit if m_per_unit is not None else UNIT_M.get(doc.header.get("$INSUNITS", 0), 1.0)
    msp = doc.modelspace()

    outlines = [valid(Polygon(_points(e, s))) for e in msp.query('LWPOLYLINE POLYLINE[layer=="ROOMS"]')
                if e.is_closed and len(_points(e, s)) >= 3]
    labels = []
    for e in msp.query('TEXT MTEXT[layer=="ROOMS"]'):
        text = e.plain_text() if e.dxftype() == "MTEXT" else e.dxf.text
        labels.append((Point(e.dxf.insert.x * s, e.dxf.insert.y * s), text))

    rooms = []
    for k, poly in enumerate(outlines):
        kinds = [_room_type(text) for at, text in labels if poly.contains(at)]
        kind = next((t for t in kinds if t), None)
        if kind is None:
            c = poly.representative_point()
            raise ValueError(f"room outline {k} near ({c.x:.2f}, {c.y:.2f}) m has no label naming its type")
        rooms.append({"type": kind, "polygon": [[round(x, 4), round(y, 4)] for x, y in poly.exterior.coords[:-1]]})

    doors = []
    for e in msp.query('LINE LWPOLYLINE POLYLINE[layer=="DOORS"]'):
        marker = LineString(_points(e, s))
        touched = sorted(k for k, poly in enumerate(outlines) if poly.intersects(marker))
        if len(touched) != 2:
            m = marker.interpolate(0.5, normalized=True)
            raise ValueError(f"door marker near ({m.x:.2f}, {m.y:.2f}) m must cross the shared wall of "
                             f"exactly two rooms; it touches {len(touched)}")
        if touched not in doors:
            doors.append(touched)
    return {"rooms": rooms, "doors": doors}
