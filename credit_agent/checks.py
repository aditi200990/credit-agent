"""Cross-document consistency checks: the discrepancy-detection node's logic."""
from __future__ import annotations

import re

from .fmt import inr
from .state import Discrepancy

INCOME_TOLERANCE = 0.15  # 15% gap between sources is flagged
_SUFFIXES = {"PVT", "PRIVATE", "LTD", "LIMITED", "LLP", "INC", "CO", "AND", "&"}


def _norm(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").upper().strip())


def _core_tokens(name: str | None) -> set[str]:
    return {t for t in re.findall(r"[A-Z]+", _norm(name)) if t not in _SUFFIXES and len(t) > 2}


def _gap(a: float, b: float) -> float:
    return abs(a - b) / max(a, b)


_fmt = inr


def find_discrepancies(extracted: dict) -> list[Discrepancy]:
    app = extracted["application"]
    applicant = app["applicant"]
    income_doc = extracted.get("payslip") or extracted.get("itr_summary") or {}
    bureau = extracted["bureau_report"]
    bank = extracted["bank_statement"]
    out: list[Discrepancy] = []

    # 1. Identity: name and PAN must agree across every document that carries them.
    for doc_name, doc in (("income proof", income_doc), ("bureau report", bureau)):
        if doc.get("name") and _norm(doc["name"]) != _norm(applicant["name"]):
            out.append({"code": "NAME_MISMATCH", "severity": "high",
                        "detail": f"Name on {doc_name} ('{doc['name']}') differs from application ('{applicant['name']}')."})
        if doc.get("pan") and _norm(doc["pan"]) != _norm(applicant["pan"]):
            out.append({"code": "PAN_MISMATCH", "severity": "high",
                        "detail": f"PAN on {doc_name} differs from application."})

    # 2. Employer: application vs income proof vs salary credit narration.
    app_tokens = _core_tokens(applicant.get("employer"))
    if income_doc.get("employer") and not app_tokens & _core_tokens(income_doc["employer"]):
        out.append({"code": "EMPLOYER_MISMATCH_DOCUMENT", "severity": "medium",
                    "detail": f"Employer on income proof ('{income_doc['employer']}') differs from application ('{applicant['employer']}')."})
    if applicant.get("employment_type") == "salaried" and bank.get("salary_narration"):
        if not app_tokens & _core_tokens(bank["salary_narration"]):
            out.append({"code": "EMPLOYER_MISMATCH_BANK", "severity": "high",
                        "detail": f"Salary is credited by a different entity ('{bank['salary_narration']}') than the declared employer ('{applicant['employer']}')."})

    # 3. Income: declared vs income proof vs bank credits.
    declared = app["declared_monthly_income"]
    doc_income = income_doc.get("net_monthly")
    if doc_income and _gap(declared, doc_income) > INCOME_TOLERANCE:
        out.append({"code": "INCOME_MISMATCH_DOCUMENT", "severity": "medium",
                    "detail": f"Declared income {_fmt(declared)} vs income proof {_fmt(doc_income)} ({_gap(declared, doc_income):.0%} gap)."})
    bank_income = bank.get("avg_salary_credit") or bank.get("avg_monthly_credits")
    reference = doc_income or declared
    if bank_income and _gap(reference, bank_income) > INCOME_TOLERANCE:
        out.append({"code": "INCOME_MISMATCH_BANK", "severity": "high",
                    "detail": f"Income proof shows {_fmt(reference)}/month but bank credits average {_fmt(bank_income)}/month ({_gap(reference, bank_income):.0%} gap)."})

    # 4. Obligations: recurring EMIs in the bank statement that the bureau doesn't show.
    bureau_lenders = {t for a in bureau["accounts"] for t in _core_tokens(a.get("lender"))}
    for payee, amount in bank["recurring_emis"].items():
        if not _core_tokens(payee) & bureau_lenders:
            out.append({"code": "UNDISCLOSED_OBLIGATION", "severity": "high",
                        "detail": f"Recurring EMI of {_fmt(amount)} to '{payee}' appears in the bank statement but not in the bureau report."})
    return out
