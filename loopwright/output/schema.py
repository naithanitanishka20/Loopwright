"""Canonical JSON and its hash. Same plan + same settings -> same bytes."""
import hashlib
import json

# Written at full precision: the validator rebuilds every area and length from the scale,
# so rounding it moves them all (a 99.9 m² zone read back over the 100 m² cap).
EXACT = ("m_per_unit",)


WINDOWS_DEVICE_NAMES = frozenset((
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
))


def _round(obj, ndigits=3):
    if isinstance(obj, float):
        return round(obj, ndigits)
    if isinstance(obj, dict):
        return {k: v if k in EXACT else _round(v, ndigits) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_round(v, ndigits) for v in obj]
    return obj


def canonical_json(obj, exclude=("runtime_s",)):
    """Deterministic JSON text: rounded floats, no timing fields."""
    def strip(o):
        if isinstance(o, dict):
            return {k: strip(v) for k, v in o.items() if k not in exclude}
        if isinstance(o, list):
            return [strip(v) for v in o]
        return o
    return json.dumps(_round(strip(obj)), ensure_ascii=False, separators=(",", ":"), sort_keys=False, allow_nan=False)


def safe_stem(plan_id):
    """A stable filename stem that stays in the output folder without collisions."""
    text = str(plan_id)
    stem = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in text)[:64]
    changed = stem != text
    if not stem:
        stem = "plan"
        changed = True
    if changed or stem.casefold() != stem or stem.upper() in WINDOWS_DEVICE_NAMES:
        suffix = hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]
        stem = f"{stem[:53]}-{suffix}"
    return stem


def digest(obj):
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def write_json(obj, path):
    text = json.dumps(_round(obj), ensure_ascii=False, indent=1, allow_nan=False)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
