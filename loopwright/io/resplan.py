"""Restricted loader for the ResPlan pickle format."""
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


class UnsafePickleError(pickle.UnpicklingError):
    pass


class _RestrictedUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if (module, name) in ALLOWED_GLOBALS:
            return super().find_class(module, name)
        raise UnsafePickleError(f"blocked global {module}.{name}")


def safe_loads(data: bytes):
    return _RestrictedUnpickler(io.BytesIO(data)).load()


def load_plans(path):
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
