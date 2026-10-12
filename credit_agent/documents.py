"""Loading raw documents from an application folder."""
from __future__ import annotations

import csv
import json
from pathlib import Path

# Documents every application needs, and the income proof each employment type needs.
REQUIRED = ["application", "bank_statement", "bureau_report"]
INCOME_PROOF = {"salaried": "payslip", "self_employed": "itr_summary"}

FILES = {
    "application": "application.json",
    "payslip": "payslip.txt",
    "itr_summary": "itr_summary.txt",
    "bank_statement": "bank_statement.csv",
    "bureau_report": "bureau_report.txt",
}


def load_documents(case_dir: str | Path) -> tuple[dict, list[str]]:
    """Return (documents, missing) for an application folder."""
    case_dir = Path(case_dir)
    docs: dict = {}
    for doc_type, filename in FILES.items():
        path = case_dir / filename
        if not path.exists():
            continue
        if filename.endswith(".json"):
            docs[doc_type] = json.loads(path.read_text())
        elif filename.endswith(".csv"):
            with path.open(newline="") as f:
                docs[doc_type] = list(csv.DictReader(f))
        else:
            docs[doc_type] = path.read_text()

    required = list(REQUIRED)
    emp_type = docs.get("application", {}).get("applicant", {}).get("employment_type")
    if emp_type in INCOME_PROOF:
        required.append(INCOME_PROOF[emp_type])
    missing = [d for d in required if d not in docs]
    return docs, missing
