"""Assisted import from a plan image (PNG, JPEG) or a PDF page, as rooms and door pairs for io.sketch.

Classical image processing, step by step:

1. Grey levels and an Otsu threshold: dark pixels are ink.
2. An opening with a small disc removes thin lines (door leaves and swings,
   text, furniture, dimension lines), so only thick walls remain.
3. Door gaps are closed along each wall's own direction: horizontal walls with a
   horizontal line, vertical walls with a vertical one. The space between two
   parallel walls, such as a corridor, is never bridged.
4. Each enclosed region that doesn't touch the image border is a room; a closed
   gap that touches two rooms is a door between them.
5. Rooms are grown to the wall centres, so neighbours share an edge, and traced
   along pixel edges into outlines in metres.

Works on clean, straight-on drawings: exports, scans and screenshots. Room types
are a guess (the largest room is living, rooms under 4 m² bathrooms, the rest
bedrooms), so the result is meant to be checked in the editor before solving.
"""
import io
import math

import numpy as np
from PIL import Image
from scipy import ndimage
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
from skimage.filters import threshold_otsu
from skimage.morphology import disk
from skimage.segmentation import expand_labels

DOOR_M = 0.9
MIN_ROOM_M2 = 1.0
SMALL_ROOM_M2 = 4.0
MAX_PIXELS = 40_000_000  # past this an image or rendered page needs gigabytes for the distance transform
NOTE = "Room types are guesses (largest: living, under 4 m²: bathroom, others: bedroom); check them."


def _grey(source):
    img = Image.open(io.BytesIO(source) if isinstance(source, (bytes, bytearray)) else source)
    if img.size[0] * img.size[1] > MAX_PIXELS:
        raise ValueError(f"image is {img.size[0]} x {img.size[1]} px; scale it down first")
    return np.asarray(img.convert("L"), dtype=np.uint8)


def _walls(grey):
    if grey.min() == grey.max():
        return np.zeros(grey.shape, bool), 0
    ink = grey <= threshold_otsu(grey)  # Otsu: values above the threshold are background (paper)
    t = int(round(2 * np.percentile(ndimage.distance_transform_edt(ink)[ink], 99)))
    walls = ndimage.binary_opening(ink, structure=disk(max(1, t // 4)))
    return walls, max(t, 2)


def _rooms(walls, t, gap_px):
    k = 2 * t + 1
    horiz = ndimage.binary_opening(walls, structure=np.ones((1, k), bool))
    vert = ndimage.binary_opening(walls, structure=np.ones((k, 1), bool))
    gaps = (ndimage.binary_closing(horiz, structure=np.ones((1, gap_px), bool))
            | ndimage.binary_closing(vert, structure=np.ones((gap_px, 1), bool))) & ~walls
    labels, n = ndimage.label(~(walls | gaps))
    edge = set(np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))) | {0}
    sizes = np.bincount(labels.ravel(), minlength=n + 1)
    inside = [lab for lab in range(1, n + 1) if lab not in edge]
    return labels, gaps, inside, sizes


def _trace(mask):
    boxes = []
    for y in np.flatnonzero(mask.any(axis=1)):
        d = np.diff(np.concatenate([[0], mask[y].astype(np.int8), [0]]))
        boxes += [box(s, y, e, y + 1) for s, e in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1))]
    shape = unary_union(boxes)
    parts = list(getattr(shape, "geoms", [shape]))
    return max((p for p in parts if isinstance(p, Polygon)), key=lambda p: p.area).simplify(0)


def _sketch(grey, m_per_px, area_m2, door_m):
    walls, t = _walls(grey)
    if not walls.any():
        raise ValueError("no rooms found: the image has no walls drawn in it")
    if m_per_px is None:
        if not area_m2:
            raise ValueError("give the drawing's scale: m_per_px, or the flat's area in m²")
        labels, _, inside, sizes = _rooms(walls, t, 8 * t)
        m_per_px = math.sqrt(area_m2 / max(1, sum(sizes[lab] for lab in inside)))
    labels, gaps, inside, sizes = _rooms(walls, t, int(math.ceil(1.25 * door_m / m_per_px)))
    keep = sorted((lab for lab in inside if sizes[lab] * m_per_px ** 2 >= MIN_ROOM_M2), key=lambda lab: -sizes[lab])
    if not keep:
        raise ValueError("no rooms found: no enclosed space of at least 1 m² inside the walls")

    rooms_img = np.zeros(labels.shape, np.int32)
    for idx, lab in enumerate(keep, start=1):
        rooms_img[labels == lab] = idx
    doors = []
    gap_labels, g = ndimage.label(gaps)
    for j in range(1, g + 1):
        mask = gap_labels == j
        rim = rooms_img[ndimage.binary_dilation(mask, iterations=2) & ~mask]
        counts = np.bincount(rim[rim > 0], minlength=len(keep) + 1)
        touched = [int(i) - 1 for i in np.argsort(-counts)[:2] if counts[i] > 0]
        if len(touched) == 2 and sorted(touched) not in doors:
            doors.append(sorted(touched))

    grown = expand_labels(rooms_img, distance=int(math.ceil(t / 2)))
    rooms = []
    for idx in range(1, len(keep) + 1):
        outline = _trace(grown == idx)
        net_m2 = sizes[keep[idx - 1]] * m_per_px ** 2
        kind = "living" if idx == 1 else ("bathroom" if net_m2 < SMALL_ROOM_M2 else "bedroom")
        rooms.append({"type": kind, "polygon": [[round(x * m_per_px, 4), round(y * m_per_px, 4)]
                                                for x, y in outline.exterior.coords[:-1]]})
    return {"rooms": rooms, "doors": sorted(doors), "wall_m": round(t * m_per_px, 4),
            "m_per_px": m_per_px, "notes": [NOTE]}


def read_image(source, *, m_per_px=None, area_m2=None, door_m=DOOR_M):
    """source: a path, a file object or the image bytes. Give m_per_px, or area_m2 to derive it."""
    return _sketch(_grey(source), m_per_px, area_m2, door_m)


def read_pdf(source, *, page=0, dpi=150, scale=None, m_per_px=None, area_m2=None, door_m=DOOR_M):
    """A PDF page rendered at dpi. scale is the drawing's ratio (100 for 1:100), or give m_per_px or area_m2."""
    import pdfplumber

    with pdfplumber.open(io.BytesIO(source) if isinstance(source, (bytes, bytearray)) else source) as pdf:
        if not 0 <= page < len(pdf.pages):
            raise ValueError(f"no page {page}; the PDF has {len(pdf.pages)}")
        sheet = pdf.pages[page]
        pixels = round(sheet.width * dpi / 72) * round(sheet.height * dpi / 72)
        if pixels > MAX_PIXELS:
            raise ValueError(f"page {page} at {dpi} dpi is {pixels} px; give a lower dpi")
        grey = np.asarray(sheet.to_image(resolution=dpi).original.convert("L"), dtype=np.uint8)
    if scale is not None and m_per_px is None:
        m_per_px = 0.0254 / dpi * scale
    return _sketch(grey, m_per_px, area_m2, door_m)
