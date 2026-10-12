"""Command line entry point.

    python -m credit_agent data/applications/clean_salaried
    python -m credit_agent --all --out outputs
"""
from __future__ import annotations

import argparse
from pathlib import Path

from .graph import run

DATA = Path(__file__).resolve().parent.parent / "data" / "applications"


def main() -> None:
    parser = argparse.ArgumentParser(prog="credit_agent", description="Run CreditAgent on loan application folders.")
    parser.add_argument("cases", nargs="*", help="Application folder(s)")
    parser.add_argument("--all", action="store_true", help="Run every sample application in data/applications")
    parser.add_argument("--out", default="outputs", help="Folder to write memos to (default: outputs)")
    parser.add_argument("--quiet", action="store_true", help="Don't print the node trace")
    args = parser.parse_args()

    cases = sorted(p for p in DATA.iterdir() if p.is_dir()) if args.all else [Path(c) for c in args.cases]
    if not cases:
        parser.error("pass an application folder or --all")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    for case in cases:
        state = run(case)
        memo_path = out_dir / f"{case.name}_memo.md"
        memo_path.write_text(state["memo"])
        print(f"\n▶ {case.name}: {state['decision']}  (grade {state.get('risk_grade', '-')}, memo: {memo_path})")
        if not args.quiet:
            for step in state["trace"]:
                print(f"   · {step}")


if __name__ == "__main__":
    main()
