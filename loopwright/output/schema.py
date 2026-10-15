import hashlib
import json


def _round(obj, ndigits=3):
    if isinstance(obj, float):
        return round(obj, ndigits)
    if isinstance(obj, dict):
        return {k: _round(v, ndigits) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_round(v, ndigits) for v in obj]
    return obj


def canonical_json(obj, exclude=("runtime_s",)):
    def strip(o):
        if isinstance(o, dict):
            return {k: strip(v) for k, v in o.items() if k not in exclude}
        if isinstance(o, list):
            return [strip(v) for v in o]
        return o
    return json.dumps(_round(strip(obj)), ensure_ascii=False, separators=(",", ":"), sort_keys=False, allow_nan=False)


def digest(obj):
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def write_json(obj, path):
    text = json.dumps(_round(obj), ensure_ascii=False, indent=1, allow_nan=False)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
