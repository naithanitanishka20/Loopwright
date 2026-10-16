"""Run many plans and group failures by cause."""
import collections
import json
import math
import random
import time
from multiprocessing import Pool

from loopwright.config import DEFAULT
from loopwright.solve import solve

MAX_WORKERS = 64


def run_one(job):
    plan, settings = job
    t0 = time.perf_counter()
    try:
        out, _ = solve(plan, settings)
    except Exception as exc:  # a crash is a result to triage, not a reason to stop the batch
        return {"id": plan.get("id"), "status": "crash", "cause": f"crash/{type(exc).__name__}",
                "error": str(exc)[:200], "runtime_s": round(time.perf_counter() - t0, 3)}
    failed = [c["id"] for c in out["validation"]["checks"] if c["pass"] is False]
    codes = [d["code"] for d in out["diagnostics"]]
    infeasible = "ROOM_OVER_CAP" in codes
    if out["validation"]["valid"]:
        status = "valid"
    elif infeasible and failed == ["V03"]:
        status = "infeasible"
    else:
        status = "invalid"
    top = next((c for c in codes if c not in ("REPAIRED_GEOMETRY",)), "")
    cause = status if status == "valid" else f"{status}/{failed[0] if failed else '-'}/{top or '-'}"
    m = out["metrics"]
    return {"id": out["plan_id"], "status": status, "cause": cause, "failed_rules": failed, "diagnostics": codes,
            "hubs": m["hubs"], "hub_lower_bound": m["hub_lower_bound"], "hub_minimum": m["hub_minimum"],
            "hubs_greedy": m.get("hubs_greedy"),
            "length_m": m["length_m"], "bends": m["bends"], "crossings": m["crossings"], "overlap_m": m["overlap_m"],
            "J": m["J"], "runtime_s": m["runtime_s"]}


def run_batch(plans, settings=DEFAULT, workers=4):
    if type(workers) is not int or workers < 1:
        raise ValueError("workers must be a positive integer")
    if workers > MAX_WORKERS:
        raise ValueError(f"workers must be at most {MAX_WORKERS}")
    jobs = [(p, settings) for p in plans]
    if workers <= 1:
        return [run_one(j) for j in jobs]
    with Pool(workers) as pool:
        return list(pool.imap(run_one, jobs, chunksize=4))


def sample(plans, n, seed):
    if type(n) is not int or n < 1:
        raise ValueError("sample size must be a positive integer")
    rng = random.Random(seed)
    return rng.sample(plans, min(n, len(plans)))


def p50_p95(times):
    """Runtime percentiles as every Loopwright report quotes them."""
    t = list(times)
    if not t:
        raise ValueError("at least one runtime is required")
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0
           for value in t):
        raise ValueError("runtimes must be finite non-negative numbers")
    t.sort()
    return t[len(t) // 2], t[int(len(t) * 0.95) - 1]


def report(rows, settings=DEFAULT):
    status = collections.Counter(r["status"] for r in rows)
    causes = collections.Counter(r["cause"] for r in rows if r["status"] != "valid")
    examples = collections.defaultdict(list)
    for r in rows:
        if r["status"] != "valid" and len(examples[r["cause"]]) < 3:
            examples[r["cause"]].append(str(r["id"]))
    solved = [r for r in rows if r["status"] != "crash"]
    lines = [f"# Batch report", "",
             f"Plans: {len(rows)} · zone rule: {settings.zone_link} · caps: {settings.max_area_m2:g} m², {settings.max_nodes} nodes", "",
             "| Status | Plans |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in status.most_common()]
    feasible = [r for r in rows if r["status"] in ("valid", "invalid", "crash")]
    if feasible:
        lines += ["", f"Valid on feasible plans: {status['valid']} of {len(feasible)} ({100 * status['valid'] / len(feasible):.1f}%)"]
    if solved:
        greedy = [r for r in solved if r.get("hubs_greedy") is not None]
        lines += [f"Hubs: {sum(r['hubs'] for r in solved)} against a lower bound of {sum(r['hub_lower_bound'] for r in solved)}"
                  + (f" and greedy's {sum(r['hubs_greedy'] for r in greedy)}" if greedy else ""),
                  "Runtime per plan: p50 {:.2f} s, p95 {:.2f} s".format(*p50_p95(r["runtime_s"] for r in rows))]
    if causes:
        lines += ["", "| Cause | Plans | Examples |", "|---|---|---|"]
        lines += [f"| {c} | {n} | {', '.join(examples[c])} |" for c, n in causes.most_common()]
    return "\n".join(lines) + "\n"


def write_rows(rows, path):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
