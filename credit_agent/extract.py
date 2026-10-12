"""Turn semi-structured documents into structured fields.

Extraction is rule-based so the demo runs offline and is fully reproducible.
In production this is the node where an LLM or document-AI model would sit,
with the same output schema.
"""
from __future__ import annotations

import re
from collections import defaultdict


def to_number(text: str | None) -> float | None:
    """Parse Indian-format amounts such as '1,52,000' or '9,84,000'."""
    if text is None:
        return None
    cleaned = re.sub(r"[^\d.]", "", text)
    return float(cleaned) if cleaned else None


def _field(text: str, label: str) -> str | None:
    match = re.search(rf"^\s*{re.escape(label)}\s*:\s*(.+?)\s*$", text, re.MULTILINE | re.IGNORECASE)
    return match.group(1) if match else None


def extract_payslip(text: str) -> dict:
    first_line = next(line for line in text.splitlines() if line.strip())
    return {
        "employer": first_line.strip(),
        "name": _field(text, "Employee Name"),
        "pan": _field(text, "PAN"),
        "gross_monthly": to_number(_field(text, "Gross Earnings")),
        "net_monthly": to_number(_field(text, "Net Pay")),
    }


def extract_itr(text: str) -> dict:
    gti = to_number(_field(text, "Gross Total Income"))
    return {
        "employer": _field(text, "Business Name"),
        "name": _field(text, "Assessee Name"),
        "pan": _field(text, "PAN"),
        "annual_income": gti,
        "net_monthly": round(gti / 12) if gti else None,
    }


def extract_bureau(text: str) -> dict:
    accounts = []
    for line in re.findall(r"^- (.+)$", text, re.MULTILINE):
        parts = [p.strip() for p in line.split("|")]
        account = {"type": parts[0]}
        for part in parts[1:]:
            key, _, value = part.partition(":")
            key = key.strip().lower()
            account[key] = value.strip() if key == "lender" else to_number(value)
        accounts.append(account)
    return {
        "name": _field(text, "Name"),
        "pan": _field(text, "PAN"),
        "score": int(to_number(_field(text, "Credit Score")) or 0),
        "enquiries_6m": int(to_number(_field(text, "Enquiries (last 6 months)")) or 0),
        "max_dpd_12m": int(to_number(_field(text, "Max DPD (last 12 months)")) or 0),
        "written_off": int(to_number(_field(text, "Written-off / Settled accounts")) or 0),
        "accounts": accounts,
        "total_emi": sum(a.get("emi") or 0 for a in accounts),
    }


SALARY_PATTERN = re.compile(r"\bSAL(ARY)?\b")
EMI_PATTERN = re.compile(r"\bEMI\b")
BOUNCE_PATTERN = re.compile(r"RETURN|BOUNCE|INSUFFICIENT FUNDS")


def extract_bank_statement(rows: list[dict]) -> dict:
    months = sorted({r["date"][:7] for r in rows})
    n_months = len(months) or 1

    salary_credits = [r for r in rows if r["credit"] and SALARY_PATTERN.search(r["description"])]
    all_credits = [float(r["credit"]) for r in rows if r["credit"]]
    bounces = [r for r in rows if BOUNCE_PATTERN.search(r["description"])]

    emi_by_payee: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        if r["debit"] and EMI_PATTERN.search(r["description"]):
            payee = r["description"].split("EMI", 1)[1].strip()
            emi_by_payee[payee].append(float(r["debit"]))
    recurring_emis = {p: sum(v) / len(v) for p, v in emi_by_payee.items()}

    month_end_balance = {}
    for r in rows:  # rows are chronological, so the last row per month wins
        month_end_balance[r["date"][:7]] = float(r["balance"])

    salary_narration = salary_credits[0]["description"] if salary_credits else None
    return {
        "months_covered": n_months,
        "avg_salary_credit": round(sum(float(r["credit"]) for r in salary_credits) / n_months) if salary_credits else None,
        "salary_narration": salary_narration,
        "avg_monthly_credits": round(sum(all_credits) / n_months),
        "recurring_emis": recurring_emis,
        "total_emi_observed": round(sum(recurring_emis.values())),
        "bounce_count": len(bounces),
        "avg_month_end_balance": round(sum(month_end_balance.values()) / len(month_end_balance)),
    }
