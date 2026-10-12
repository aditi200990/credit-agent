"""Evaluate CreditAgent against labelled cases.

Measures three things a credit team would care about:
  1. Decision accuracy       did the agent reach the right outcome?
  2. Discrepancy detection   precision and recall on the red flags it raises
  3. Memo grounding          every figure in the memo commentary traces to source data

    python evals/run_evals.py
Exits non-zero if any case fails, so it can gate CI.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from credit_agent import run  # noqa: E402
from credit_agent.memo import _facts, ungrounded_numbers  # noqa: E402


def commentary(memo: str) -> str:
    match = re.search(r"## Analyst commentary\n(.+)", memo, re.DOTALL)
    return match.group(1) if match else ""


def main() -> int:
    expected = json.loads((ROOT / "evals" / "expected.json").read_text())
    tp = fp = fn = correct = grounded = 0
    rows = []

    for case, truth in expected.items():
        state = run(ROOT / "data" / "applications" / case)
        found = {d["code"] for d in state["discrepancies"]}
        want = set(truth["discrepancies"])
        tp += len(found & want)
        fp += len(found - want)
        fn += len(want - found)
        ok_decision = state["decision"] == truth["decision"]
        correct += ok_decision
        bad_numbers = ungrounded_numbers(commentary(state["memo"]), _facts(state))
        grounded += not bad_numbers
        rows.append((case, truth["decision"], state["decision"], ok_decision,
                     f"{len(found & want)}/{len(want)}", len(found - want), state["memo_source"], not bad_numbers))

    n = len(expected)
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0

    print(f"{'case':<26}{'expected':<10}{'actual':<10}{'ok':<4}{'flags hit':<11}{'false +':<9}{'memo':<14}grounded")
    for case, exp, act, ok, hit, fpos, src, gr in rows:
        print(f"{case:<26}{exp:<10}{act:<10}{'✓' if ok else '✗':<4}{hit:<11}{fpos:<9}{src:<14}{'✓' if gr else '✗'}")
    print(f"\nDecision accuracy     {correct}/{n} ({correct / n:.0%})")
    print(f"Discrepancy precision {precision:.0%}   recall {recall:.0%}")
    print(f"Memo grounding        {grounded}/{n} memos with every figure traceable to source data")

    return 0 if correct == n and precision == recall == 1.0 and grounded == n else 1


if __name__ == "__main__":
    sys.exit(main())
