"""Load ResPlan plans safely.

The ResPlan pickle references only the three globals in ALLOWED_GLOBALS. A
restricted unpickler refuses anything else, so a tampered or substituted file
can't run code on load.
"""
import io
import pathlib
import pickle
import zipfile

ALLOWED_GLOBALS = frozenset({
    ("shapely.io", "from_wkb"),
    ("numpy._core.multiarray", "scalar"),
    ("numpy", "dtype"),
})
KEY_ALIASES = {"balacony": "balcony"}
MAX_PICKLE_BYTES = 512 * 1024 * 1024


class UnsafePickleError(pickle.UnpicklingError):
    """The pickle referenced a global outside ALLOWED_GLOBALS."""


class _RestrictedUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if (module, name) in ALLOWED_GLOBALS:
            return super().find_class(module, name)
        raise UnsafePickleError(f"blocked global {module}.{name}")


def safe_loads(data: bytes):
    return _RestrictedUnpickler(io.BytesIO(data)).load()


def _check_pickle_size(size):
    if size > MAX_PICKLE_BYTES:
        raise ValueError(f"pickle exceeds the maximum allowed size ({MAX_PICKLE_BYTES} bytes)")


def _normalize_plans(plans):
    if not isinstance(plans, list) or any(not isinstance(plan, dict) for plan in plans):
        raise ValueError("ResPlan pickle must contain a list of plan mappings")
    return [normalize_keys(plan) for plan in plans]


def load_plans(path):
    """Load every plan from ResPlan.zip (containing one .pkl) or a bare .pkl."""
    path = pathlib.Path(path)
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as z:
            member = next((i for i in z.infolist() if i.filename.endswith(".pkl")), None)
            if member is None:
                raise FileNotFoundError(f"no .pkl inside {path}")
            _check_pickle_size(member.file_size)
            with z.open(member) as f:
                plans = _RestrictedUnpickler(io.BufferedReader(f, 1 << 20)).load()
    else:
        _check_pickle_size(path.stat().st_size)
        with open(path, "rb") as f:
            plans = _RestrictedUnpickler(f).load()
    return _normalize_plans(plans)


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
