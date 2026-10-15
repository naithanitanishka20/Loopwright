"""Command line: loopwright solve | validate."""
import argparse
import json
import os
import pathlib
import sys

from loopwright.config import DEFAULT, ZONE_LINKS

DEFAULT_DATA = os.environ.get("LOOPWRIGHT_DATA", "data/ResPlan.zip")


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


def cmd_solve(args):
    from loopwright.output.overlay import render_svg
    from loopwright.output.schema import digest, write_json
    from loopwright.output.viewer import render_viewer
    from loopwright.solve import solve

    plan = _load_plan(args)
    out, model = solve(plan, _settings(args))
    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = _safe_stem(out["plan_id"])
    write_json(out, out_dir / f"{stem}.json")
    (out_dir / f"{stem}.svg").write_text(render_svg(model, out), encoding="utf-8")
    (out_dir / f"{stem}.html").write_text(render_viewer(model, out), encoding="utf-8")
    m = out["metrics"]
    failed = [c["id"] for c in out["validation"]["checks"] if c["pass"] is False]
    print(f"plan {stem}: hubs {m['hubs']} (bound {m['hub_lower_bound']}), cable {m['length_m']} m, "
          f"bends {m['bends']}, J {m['J']}, valid {out['validation']['valid']}"
          + (f" (failed: {', '.join(failed)})" if failed else "") + f", hash {digest(out)[:12]}")
    print(f"wrote {out_dir / (stem + '.json')}, {stem}.svg and {stem}.html (viewer)")
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


def cmd_validate(args):
    from loopwright.validate.rules import validate

    with open(args.output, encoding="utf-8") as f:
        out = json.load(f)
    result = validate(_load_plan(args), out, _settings(args))
    for c in result["checks"]:
        state = {True: "pass", False: "FAIL", None: "skip"}[c["pass"]]
        print(f"{c['id']}  {state}  {c.get('detail', '') if c['pass'] is not True else ''}".rstrip())
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


def main(argv=None):
    p = argparse.ArgumentParser(prog="loopwright", description="Hub placement and closed-ring cable routing")
    sub = p.add_subparsers(dest="command", required=True)
    ix = sub.add_parser("index", help="write index.html listing every solved plan in a folder")
    ix.add_argument("folder", nargs="?", default="out")
    b = sub.add_parser("batch", help="run many ResPlan plans and group failures by cause")
    b.add_argument("--data", default=DEFAULT_DATA)
    b.add_argument("--split", choices=("train", "val", "test", "augmented"), help="a ResPlan split from split.json")
    b.add_argument("--split-file", help="path to split.json (default: next to --data)")
    b.add_argument("--sample", type=int, help="random sample size (default: all plans)")
    b.add_argument("--seed", type=int, default=7)
    b.add_argument("--workers", type=int, default=4)
    b.add_argument("--report", default="bench/report.md")
    b.add_argument("--zone-link", choices=ZONE_LINKS)
    b.add_argument("--max-nodes", type=int)
    b.add_argument("--max-area", type=float)
    for name in ("solve", "validate"):
        q = sub.add_parser(name)
        if name == "validate":
            q.add_argument("output", help="a loopwright/2 JSON file")
        q.add_argument("--id", help="ResPlan plan id")
        q.add_argument("--data", default=DEFAULT_DATA, help="ResPlan.zip or .pkl (default: %(default)s)")
        q.add_argument("--json", help="an organisers' plan JSON instead of a ResPlan id")
        q.add_argument("--zone-link", choices=ZONE_LINKS, help="assumptions Q1")
        q.add_argument("--max-nodes", type=int, help="assumptions Q4")
        q.add_argument("--max-area", type=float, help="area cap in m²")
        if name == "solve":
            q.add_argument("--out", default="out", help="output folder (default: %(default)s)")
    args = p.parse_args(argv)
    if args.command == "batch":
        return cmd_batch(args)
    if args.command == "index":
        return cmd_index(args)
    if not args.json and not args.id:
        p.error("give --id (ResPlan) or --json (organisers' file)")
    return cmd_solve(args) if args.command == "solve" else cmd_validate(args)


if __name__ == "__main__":
    sys.exit(main())
