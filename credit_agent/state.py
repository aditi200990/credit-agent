"""Shared state passed between LangGraph nodes."""
from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class Discrepancy(TypedDict):
    code: str          # machine-readable, e.g. "INCOME_MISMATCH_BANK"
    severity: str      # "high" | "medium" | "low"
    detail: str        # human-readable explanation with the numbers involved


class PolicyResult(TypedDict):
    rule: str
    passed: bool
    hard: bool         # hard rules decline; soft rules refer
    actual: Any
    threshold: Any


class CreditState(TypedDict, total=False):
    case_dir: str
    documents: dict[str, Any]            # raw files keyed by document type
    missing_documents: list[str]
    extracted: dict[str, Any]            # structured fields per document
    discrepancies: list[Discrepancy]
    metrics: dict[str, Any]
    policy_results: list[PolicyResult]
    risk_grade: str
    risk_points: int
    decision: str                        # APPROVE | REFER | DECLINE | INCOMPLETE
    decision_reasons: list[str]
    memo: str
    memo_source: str                     # "template" | "llm" | "llm_rejected"
    trace: Annotated[list[str], operator.add]  # appended to by every node
