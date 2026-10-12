"""Financial analysis, credit policy and risk grading."""
from __future__ import annotations

from .fmt import inr
from .state import Discrepancy, PolicyResult

# Illustrative policy, not any real lender's.
POLICY = {
    "min_score": 700,
    "max_dpd_12m": 30,
    "max_written_off": 0,
    "max_foir": 0.50,
    "min_monthly_income": 25000,
    "max_enquiries_6m": 4,
    "max_bounces": 1,
}


def emi(principal: float, annual_rate_pct: float, months: int) -> float:
    """Standard reducing-balance EMI."""
    r = annual_rate_pct / 1200
    if r == 0:
        return principal / months
    factor = (1 + r) ** months
    return principal * r * factor / (factor - 1)


def compute_metrics(extracted: dict) -> dict:
    app = extracted["application"]
    loan = app["loan"]
    income_doc = extracted.get("payslip") or extracted.get("itr_summary") or {}
    bank = extracted["bank_statement"]
    bureau = extracted["bureau_report"]

    income_sources = {
        "declared": app["declared_monthly_income"],
        "income_proof": income_doc.get("net_monthly"),
        "bank": bank.get("avg_salary_credit") or bank.get("avg_monthly_credits"),
    }
    # Conservative: underwrite on the lowest verified income.
    assessed_income = min(v for v in income_sources.values() if v)
    # Use whichever source shows more existing debt (catches undisclosed loans).
    existing_emi = max(bureau["total_emi"], bank["total_emi_observed"])
    proposed_emi = round(emi(loan["amount"], loan["annual_rate_pct"], loan["tenure_months"]))

    return {
        "income_sources": income_sources,
        "assessed_monthly_income": assessed_income,
        "existing_emi": existing_emi,
        "proposed_emi": proposed_emi,
        "foir": round((existing_emi + proposed_emi) / assessed_income, 3),
        "foir_on_declared": round((bureau["total_emi"] + proposed_emi) / app["declared_monthly_income"], 3),
        "loan_to_annual_income": round(loan["amount"] / (assessed_income * 12), 2),
        "avg_month_end_balance": bank["avg_month_end_balance"],
        "bounce_count": bank["bounce_count"],
        "score": bureau["score"],
        "max_dpd_12m": bureau["max_dpd_12m"],
        "enquiries_6m": bureau["enquiries_6m"],
        "written_off": bureau["written_off"],
    }


def check_policy(m: dict) -> list[PolicyResult]:
    p = POLICY
    rules = [
        ("Bureau score", m["score"] >= p["min_score"], True, m["score"], f">= {p['min_score']}"),
        ("Max DPD (12m)", m["max_dpd_12m"] <= p["max_dpd_12m"], True, m["max_dpd_12m"], f"<= {p['max_dpd_12m']}"),
        ("Written-off / settled accounts", m["written_off"] <= p["max_written_off"], True, m["written_off"], f"<= {p['max_written_off']}"),
        ("FOIR on assessed income", m["foir"] <= p["max_foir"], True, f"{m['foir']:.1%}", f"<= {p['max_foir']:.0%}"),
        ("Minimum monthly income", m["assessed_monthly_income"] >= p["min_monthly_income"], True,
         f"{inr(m['assessed_monthly_income'])}", f">= {inr(p['min_monthly_income'])}"),
        ("Enquiries (6m)", m["enquiries_6m"] <= p["max_enquiries_6m"], False, m["enquiries_6m"], f"<= {p['max_enquiries_6m']}"),
        ("Cheque / ACH bounces (3m)", m["bounce_count"] <= p["max_bounces"], False, m["bounce_count"], f"<= {p['max_bounces']}"),
        ("Avg balance covers proposed EMI", m["avg_month_end_balance"] >= m["proposed_emi"], False,
         f"{inr(m['avg_month_end_balance'])}", f">= {inr(m['proposed_emi'])}"),
    ]
    return [{"rule": r, "passed": ok, "hard": hard, "actual": a, "threshold": t} for r, ok, hard, a, t in rules]


def risk_grade(m: dict, discrepancies: list[Discrepancy]) -> tuple[str, int]:
    """Transparent points-based grade (A best, E worst)."""
    points = 100
    points -= max(0, (750 - m["score"]) // 10) * 3          # 3 pts per 10 score points below 750
    points -= max(0, round((m["foir"] - 0.35) * 100))       # 1 pt per FOIR point above 35%
    points -= 20 if m["max_dpd_12m"] > 30 else (8 if m["max_dpd_12m"] > 0 else 0)
    points -= max(0, m["enquiries_6m"] - 2) * 3
    points -= m["bounce_count"] * 5
    points -= sum({"high": 10, "medium": 5, "low": 2}[d["severity"]] for d in discrepancies)
    points = max(0, points)
    grade = next(g for g, cutoff in (("A", 85), ("B", 70), ("C", 55), ("D", 40), ("E", 0)) if points >= cutoff)
    return grade, points


def decide(policy: list[PolicyResult], discrepancies: list[Discrepancy]) -> tuple[str, list[str]]:
    high = [d for d in discrepancies if d["severity"] == "high"]
    hard_fails = [r for r in policy if r["hard"] and not r["passed"]]
    soft_fails = [r for r in policy if not r["hard"] and not r["passed"]]

    if high:
        # Data can't be trusted until a human resolves it, so this beats any policy outcome.
        return "REFER", [f"{len(high)} high-severity discrepancy(ies) need manual verification before a credit decision."] + \
            [f"Policy would also fail: {r['rule']} ({r['actual']} vs {r['threshold']})." for r in hard_fails]
    if hard_fails:
        return "DECLINE", [f"Hard policy breach: {r['rule']} ({r['actual']} vs {r['threshold']})." for r in hard_fails]
    if soft_fails or discrepancies:
        return "REFER", [f"Soft policy exception: {r['rule']} ({r['actual']} vs {r['threshold']})." for r in soft_fails] + \
            [f"Discrepancy to clarify: {d['detail']}" for d in discrepancies]
    return "APPROVE", ["All policy rules passed and documents are consistent."]
