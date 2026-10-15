from __future__ import annotations

import argparse
import json

from .config import DEFAULT
from .validator import DesignValidationError, load_design


def _parser():
    parser = argparse.ArgumentParser(prog="loopwright")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("config", help="print the default settings")
    validate = commands.add_parser("validate", help="validate a design JSON file")
    validate.add_argument("path")
    validate.add_argument("--id", dest="plan_id")
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    if args.command == "config":
        print(json.dumps(DEFAULT.as_dict(), sort_keys=True))
        return 0

    try:
        design = load_design(args.path)
    except DesignValidationError as exc:
        print(json.dumps({"valid": False, "issues": exc.issues}, sort_keys=True))
        return 1
    if args.plan_id is not None and str(design["plan_id"]) != args.plan_id:
        print(json.dumps({"valid": False, "issues": ["plan_id does not match --id"]}, sort_keys=True))
        return 1
    print(json.dumps({"valid": True, "issues": []}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
