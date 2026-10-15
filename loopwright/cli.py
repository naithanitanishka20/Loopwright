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


def cmd_config(args):
    print(json.dumps(DEFAULT.as_dict(), sort_keys=True))
    return 0


def cmd_solve(args):
    from loopwright.output.overlay import render_svg
    from loopwright.output.schema import digest, write_json
    from loopwright.solve import solve

    plan = _load_plan(args)
    out, model = solve(plan, _settings(args))
    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = str(out["plan_id"])
    write_json(out, out_dir / f"{stem}.json")
    (out_dir / f"{stem}.svg").write_text(render_svg(model, out), encoding="utf-8")
    m = out["metrics"]
    failed = [c["id"] for c in out["validation"]["checks"] if c["pass"] is False]
    print(f"plan {stem}: hubs {m['hubs']} (bound {m['hub_lower_bound']}), cable {m['length_m']} m, "
          f"bends {m['bends']}, J {m['J']}, valid {out['validation']['valid']}"
          + (f" (failed: {', '.join(failed)})" if failed else "") + f", hash {digest(out)[:12]}")
    print(f"wrote {out_dir / (stem + '.json')} and {out_dir / (stem + '.svg')}")
    return 0


def _print_checks(checks):
    for c in checks:
        state = {True: "pass", False: "FAIL", None: "skip"}[c["pass"]]
        print(f"{c['id']}  {state}  {c.get('detail', '') if c['pass'] is not True else ''}".rstrip())


def cmd_validate(args):
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
        print("valid (structure only; give --id or --json to check rules V00-V14)")
        return 0

    from loopwright.validate.rules import validate

    result = validate(_load_plan(args), out, _settings(args))
    _print_checks([{"id": "structure", "pass": True}] + result["checks"])
    print("valid" if result["valid"] else "INVALID")
    return 0 if result["valid"] else 1


def main(argv=None):
    p = argparse.ArgumentParser(prog="loopwright", description="Hub placement and closed-ring cable routing")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("config", help="print the default settings as JSON")
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
    if args.command == "config":
        return cmd_config(args)
    if args.command == "solve":
        if not args.json and not args.id:
            p.error("give --id (ResPlan) or --json (organisers' file)")
        return cmd_solve(args)
    return cmd_validate(args)


if __name__ == "__main__":
    sys.exit(main())
