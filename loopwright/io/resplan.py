"""Load ResPlan plans safely.

The ResPlan pickle references only the three globals in ALLOWED_GLOBALS. A
restricted unpickler refuses anything else, so a tampered or substituted file
can't run code on load.
"""
import io
import json
import pathlib
import pickle
import sqlite3
import zipfile
import zlib

ALLOWED_GLOBALS = frozenset({
    ("shapely.io", "from_wkb"),
    ("numpy._core.multiarray", "scalar"),
    ("numpy", "dtype"),
})
KEY_ALIASES = {"balacony": "balcony"}


class UnsafePickleError(pickle.UnpicklingError):
    """The pickle referenced a global outside ALLOWED_GLOBALS."""


class _RestrictedUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if (module, name) in ALLOWED_GLOBALS:
            return super().find_class(module, name)
        raise UnsafePickleError(f"blocked global {module}.{name}")


def safe_loads(data: bytes):
    return _RestrictedUnpickler(io.BytesIO(data)).load()


def load_plans(path):
    """Load every plan from ResPlan.zip (containing one .pkl) or a bare .pkl."""
    path = pathlib.Path(path)
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as z:
            name = next((i.filename for i in z.infolist() if i.filename.endswith(".pkl")), None)
            if name is None:
                raise FileNotFoundError(f"no .pkl inside {path}")
            with z.open(name) as f:
                plans = _RestrictedUnpickler(io.BufferedReader(f, 1 << 20)).load()
    else:
        with open(path, "rb") as f:
            plans = _RestrictedUnpickler(f).load()
    return [normalize_keys(p) for p in plans]


def normalize_keys(plan):
    for old, new in KEY_ALIASES.items():
        if old in plan and new not in plan:
            plan[new] = plan.pop(old)
    return plan


def get_plan(plans, plan_id):
    for p in plans:
        if str(p.get("id")) == str(plan_id):
            return p
    raise KeyError(f"plan {plan_id} not found")


class PlanStore:
    """Every plan in one SQLite file, each a compressed pickle read back through the restricted unpickler,
    so a server holds one plan at a time instead of all 17,000 (about 1.4 GB). The split travels inside
    it. Written by scripts/plan_store.py."""

    def __init__(self, path):
        self.uri = pathlib.Path(path).resolve().as_uri() + "?mode=ro"

    def _rows(self, sql, args=()):
        db = sqlite3.connect(self.uri, uri=True)
        try:
            return db.execute(sql, args).fetchall()
        finally:
            db.close()

    def get(self, plan_id):
        try:
            key = int(plan_id)
        except (TypeError, ValueError):
            return None
        rows = self._rows("SELECT data FROM plans WHERE id = ?", (key,))
        return safe_loads(zlib.decompress(rows[0][0])) if rows else None

    def ids(self):
        return [row[0] for row in self._rows("SELECT id FROM plans ORDER BY id")]

    def split(self):
        rows = self._rows("SELECT value FROM meta WHERE key = 'split'")
        return json.loads(rows[0][0]) if rows else {}


def write_store(plans, split, target):
    """Write `plans` and the dataset's `split` as a PlanStore at `target`, replacing any file there."""
    target = pathlib.Path(target)
    target.unlink(missing_ok=True)
    db = sqlite3.connect(target)
    try:
        db.execute("CREATE TABLE plans (id INTEGER PRIMARY KEY, data BLOB NOT NULL)")
        db.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.executemany("INSERT INTO plans VALUES (?, ?)",
                       ((int(p["id"]), zlib.compress(pickle.dumps(p, protocol=4), 6)) for p in plans))
        db.execute("INSERT INTO meta VALUES ('split', ?)", (json.dumps(split),))
        db.commit()
    finally:
        db.close()
