"""Command line: loopwright solve | validate | index | batch | results | charts | site | serve | config."""
import argparse
import json
import math
import os
import pathlib
import sys

from loopwright.config import DEFAULT, ZONE_LINKS

DEFAULT_DATA = os.environ.get("LOOPWRIGHT_DATA", "data/ResPlan.zip")


def _positive_int(value):
    parsed = int(value)
    if str(parsed) != value or parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _positive_float(value):
    parsed = float(value)
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError("must be a finite positive number")
    return parsed


def _worker_count(value):
    parsed = _positive_int(value)
    from loopwright.batch import MAX_WORKERS

    if parsed > MAX_WORKERS:
        raise argparse.ArgumentTypeError(f"must be at most {MAX_WORKERS}")
    return parsed


def _load_plan(args):
    if args.json:
        from loopwright.io.organiser import load_json

        return load_json(args.json)
    from loopwright.io.resplan import get_plan, load_plans

    return get_plan(load_plans(args.data), args.id)


def _settings(args):
    return DEFAULT.with_overrides(zone_link=args.zone_link, max_nodes=args.max_nodes, max_area_m2=args.max_area)


def _safe_stem(plan_id):
    from loopwright.output.schema import safe_stem

    return safe_stem(plan_id)


def cmd_config(args):
    print(json.dumps(DEFAULT.as_dict(), sort_keys=True))
    return 0


def cmd_solve(args):
    from loopwright.io.edits import door_parts
    from loopwright.output.installer import installer_csv, installer_data, render_installer
    from loopwright.output.overlay import render_svg
    from loopwright.output.schema import digest, write_json
    from loopwright.output.viewer import render_viewer
    from loopwright.solve import solve

    plan = _load_plan(args)
    out, model = solve(plan, _settings(args))
    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = _safe_stem(out["plan_id"])
    doors = door_parts(plan)
    write_json(out, out_dir / f"{stem}.json")
    (out_dir / f"{stem}.svg").write_text(render_svg(model, out), encoding="utf-8")
    (out_dir / f"{stem}.html").write_text(render_viewer(model, out), encoding="utf-8")
    (out_dir / f"{stem}.installer.html").write_text(render_installer(model, out, doors), encoding="utf-8")
    (out_dir / f"{stem}.installer.csv").write_text(installer_csv(installer_data(out, doors)), encoding="utf-8")
    m = out["metrics"]
    failed = [c["id"] for c in out["validation"]["checks"] if c["pass"] is False]
    print(f"plan {stem}: hubs {m['hubs']} (bound {m['hub_lower_bound']}), cable {m['length_m']} m, "
          f"bends {m['bends']}, J {m['J']}, valid {out['validation']['valid']}"
          + (f" (failed: {', '.join(failed)})" if failed else "") + f", hash {digest(out)[:12]}")
    print(f"wrote {out_dir / (stem + '.json')}, {stem}.svg, {stem}.html (viewer) and {stem}.installer.html/.csv")
    return 0


def cmd_index(args):
    from loopwright.output.viewer import render_index

    folder = pathlib.Path(args.folder)
    designs = []
    for path in sorted(folder.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        if d.get("schema") == "loopwright/2" and (folder / f"{_safe_stem(d['plan_id'])}.html").exists():
            designs.append(d)
    (folder / "index.html").write_text(render_index(designs), encoding="utf-8")
    print(f"wrote {folder / 'index.html'} listing {len(designs)} plans")
    return 0


def _print_checks(checks):
    for c in checks:
        state = {True: "pass", False: "FAIL", None: "skip"}[c["pass"]]
        print(f"{c['id']}  {state}  {c.get('detail', '') if c['pass'] is not True else ''}".rstrip())


def cmd_validate(args):
    """Structure first (types, finite numbers, schema keys), then rules V00-V16 against the plan."""
    from loopwright.validate.structure import DesignValidationError, load_design

    try:
        out = load_design(args.output)
    except DesignValidationError as exc:
        _print_checks([{"id": "structure", "pass": False, "detail": issue} for issue in exc.issues])
        print("INVALID")
        return 1
    if args.id is not None and str(out["plan_id"]) != args.id:
        _print_checks([{"id": "structure", "pass": False, "detail": f"plan_id {out['plan_id']!r} does not match --id {args.id}"}])
        print("INVALID")
        return 1
    if not args.json and not args.id:
        _print_checks([{"id": "structure", "pass": True}])
        print("valid (structure only; give --id or --json to check rules V00-V16)")
        return 0

    from loopwright.validate.rules import validate

    result = validate(_load_plan(args), out, _settings(args))
    _print_checks([{"id": "structure", "pass": True}] + result["checks"])
    print("valid" if result["valid"] else "INVALID")
    return 0 if result["valid"] else 1


def cmd_batch(args):
    from loopwright.batch import report, run_batch, sample, write_rows
    from loopwright.io.resplan import load_plans

    plans = load_plans(args.data)
    if args.split:
        split_file = pathlib.Path(args.split_file or pathlib.Path(args.data).with_name("split.json"))
        with open(split_file, encoding="utf-8") as f:
            wanted = set(json.load(f)[args.split])
        plans = [p for p in plans if p.get("id") in wanted]
        print(f"{args.split} split: {len(plans)} plans")
    if args.sample:
        plans = sample(plans, args.sample, args.seed)
    settings = _settings(args)
    rows = run_batch(plans, settings, workers=args.workers)
    out = pathlib.Path(args.report)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_rows(rows, out.with_suffix(".jsonl"))
    text = report(rows, settings)
    out.write_text(text, encoding="utf-8")
    print(text)
    return 0


def cmd_results(args):
    from loopwright.results import results_file

    text = results_file(args.runs)
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(text)
    return 0


def cmd_charts(args):
    from loopwright.charts import extra_hubs_chart, runtime_chart
    from loopwright.results import load_rows

    rows = [r for path in args.runs for r in load_rows(path)]
    if args.runtime:
        times, label = [r["runtime_s"] for r in load_rows(args.runtime)], "single process"
    else:
        times, label = [r["runtime_s"] for r in rows], "parallel batch"
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "extra-hubs.svg").write_text(extra_hubs_chart(rows), encoding="utf-8")
    (out / "runtime.svg").write_text(runtime_chart(times, label=label), encoding="utf-8")
    print(f"wrote {out / 'extra-hubs.svg'} and {out / 'runtime.svg'}")
    return 0


def cmd_site(args):
    from loopwright.config import DEFAULT
    from loopwright.io.resplan import get_plan, load_plans
    from loopwright.site import build_site

    plans = load_plans(args.data)
    hero, rule, compare = (get_plan(plans, pid) for pid in (2916, 16448, 11282))
    drawings = {
        "hero": (hero, DEFAULT, {"live": True}),
        "rule_strict": (rule, DEFAULT, {}),
        "rule_through": (rule, DEFAULT.with_overrides(zone_link="through_rooms"), {}),
        "before": (compare, DEFAULT.with_overrides(node_rule="pole", separate_lanes=False), {}),
        "after": (compare, DEFAULT, {}),
    }
    n = build_site(args.out, drawings, args.bench)["numbers"]
    print(f"wrote {args.out}/data.js and {args.out}/assets: {n['valid']:,} of {n['feasible']:,} feasible plans valid, "
          f"{n['hubs']:,} hubs")
    return 0


def cmd_serve(args):
    import uvicorn

    from loopwright.api.app import create_app

    data = args.data if pathlib.Path(args.data).exists() else None
    app = create_app(data_path=data, allowed_hosts=("127.0.0.1", "localhost", args.host))
    print(f"Loopwright on http://{args.host}:{args.port}/  (ResPlan: {data or 'not found; sketch, import and edit only'})")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="loopwright", description="Hub placement and closed-ring cable routing")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("config", help="print the default settings as JSON")
    ix = sub.add_parser("index", help="write index.html listing every solved plan in a folder")
    ix.add_argument("folder", nargs="?", default="out")
    rs = sub.add_parser("results", help="write the results table from batch records (.jsonl)")
    rs.add_argument("runs", nargs="+", help="batch .jsonl files; each becomes a row named after the file")
    rs.add_argument("--out", default="bench/results.md")
    ch = sub.add_parser("charts", help="write the slide figures (SVG) from batch records (.jsonl)")
    ch.add_argument("runs", nargs="+", help="batch .jsonl files; their plans are pooled")
    ch.add_argument("--runtime", help="records of a one-worker batch for the runtime figure "
                                      "(default: the runs' own times)")
    ch.add_argument("--out", default="docs/figures")
    st = sub.add_parser("site", help="regenerate the product site's drawings, charts and numbers")
    st.add_argument("--out", default="site")
    st.add_argument("--bench", default="bench", help="folder of batch records (default: %(default)s)")
    st.add_argument("--data", default=DEFAULT_DATA, help="ResPlan.zip (default: %(default)s)")
    sv = sub.add_parser("serve", help="run the demo app on this machine")
    sv.add_argument("--host", default="127.0.0.1", help="address to listen on (default: %(default)s)")
    sv.add_argument("--port", type=int, default=8000)
    sv.add_argument("--data", default=DEFAULT_DATA, help="ResPlan.zip for plans by id (default: %(default)s)")
    b = sub.add_parser("batch", help="run many ResPlan plans and group failures by cause")
    b.add_argument("--data", default=DEFAULT_DATA)
    b.add_argument("--split", choices=("train", "val", "test", "augmented"), help="a ResPlan split from split.json")
    b.add_argument("--split-file", help="path to split.json (default: next to --data)")
    b.add_argument("--sample", type=_positive_int, help="random sample size (default: all plans)")
    b.add_argument("--seed", type=int, default=7)
    b.add_argument("--workers", type=_worker_count, default=4)
    b.add_argument("--report", default="bench/report.md")
    b.add_argument("--zone-link", choices=ZONE_LINKS)
    b.add_argument("--max-nodes", type=_positive_int)
    b.add_argument("--max-area", type=_positive_float)
    for name in ("solve", "validate"):
        q = sub.add_parser(name)
        if name == "validate":
            q.add_argument("output", help="a loopwright/2 JSON file")
        q.add_argument("--id", help="ResPlan plan id")
        q.add_argument("--data", default=DEFAULT_DATA, help="ResPlan.zip or .pkl (default: %(default)s)")
        q.add_argument("--json", help="an organisers' plan JSON instead of a ResPlan id")
        q.add_argument("--zone-link", choices=ZONE_LINKS, help="assumptions Q1")
        q.add_argument("--max-nodes", type=_positive_int, help="assumptions Q4")
        q.add_argument("--max-area", type=_positive_float, help="area cap in m²")
        if name == "solve":
            q.add_argument("--out", default="out", help="output folder (default: %(default)s)")
    args = p.parse_args(argv)
    if args.command == "config":
        return cmd_config(args)
    if args.command == "batch":
        return cmd_batch(args)
    if args.command == "index":
        return cmd_index(args)
    if args.command == "serve":
        return cmd_serve(args)
    if args.command == "results":
        return cmd_results(args)
    if args.command == "charts":
        return cmd_charts(args)
    if args.command == "site":
        return cmd_site(args)
    if args.command == "solve":
        if not args.json and not args.id:
            p.error("give --id (ResPlan) or --json (organisers' file)")
        return cmd_solve(args)
    return cmd_validate(args)


if __name__ == "__main__":
    sys.exit(main())
