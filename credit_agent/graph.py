"""The LangGraph workflow: eight nodes, one conditional branch."""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from . import analysis, checks, documents, extract, memo
from .fmt import inr
from .state import CreditState


def ingest(state: CreditState) -> dict:
    docs, missing = documents.load_documents(state["case_dir"])
    return {"documents": docs, "missing_documents": missing,
            "trace": [f"ingest: loaded {sorted(docs)}" + (f"; missing {missing}" if missing else "")]}


def route_after_ingest(state: CreditState) -> str:
    return "incomplete" if state["missing_documents"] else "extract"


def incomplete(state: CreditState) -> dict:
    app_id = state["documents"].get("application", {}).get("application_id", "UNKNOWN")
    text = (f"# Credit Memo — {app_id}\n\n**Recommendation:** {memo.DECISION_BADGE['INCOMPLETE']}\n\n"
            "Missing documents:\n" + "\n".join(f"- {d}" for d in state["missing_documents"]) + "\n")
    return {"decision": "INCOMPLETE", "decision_reasons": [f"Missing: {', '.join(state['missing_documents'])}"],
            "memo": text, "memo_source": "template", "trace": ["incomplete: short-circuited, documents missing"]}


def extract_node(state: CreditState) -> dict:
    d = state["documents"]
    out = {
        "application": d["application"],
        "bank_statement": extract.extract_bank_statement(d["bank_statement"]),
        "bureau_report": extract.extract_bureau(d["bureau_report"]),
    }
    if "payslip" in d:
        out["payslip"] = extract.extract_payslip(d["payslip"])
    if "itr_summary" in d:
        out["itr_summary"] = extract.extract_itr(d["itr_summary"])
    return {"extracted": out, "trace": [f"extract: structured {len(out)} documents"]}


def detect_discrepancies(state: CreditState) -> dict:
    found = checks.find_discrepancies(state["extracted"])
    return {"discrepancies": found,
            "trace": [f"discrepancies: {len(found)} found {[d['code'] for d in found]}"]}


def analyze(state: CreditState) -> dict:
    m = analysis.compute_metrics(state["extracted"])
    return {"metrics": m, "trace": [f"analyze: assessed income {inr(m['assessed_monthly_income'])}, FOIR {m['foir']:.1%}"]}


def policy_check(state: CreditState) -> dict:
    results = analysis.check_policy(state["metrics"])
    failed = [r["rule"] for r in results if not r["passed"]]
    return {"policy_results": results, "trace": [f"policy: {len(results) - len(failed)}/{len(results)} passed; failed {failed}"]}


def risk_grade(state: CreditState) -> dict:
    grade, points = analysis.risk_grade(state["metrics"], state["discrepancies"])
    return {"risk_grade": grade, "risk_points": points, "trace": [f"risk: grade {grade} ({points}/100)"]}


def decide(state: CreditState) -> dict:
    decision, reasons = analysis.decide(state["policy_results"], state["discrepancies"])
    return {"decision": decision, "decision_reasons": reasons, "trace": [f"decide: {decision}"]}


def write_memo(state: CreditState) -> dict:
    text, source = memo.build_memo(state)
    return {"memo": text, "memo_source": source, "trace": [f"memo: written ({source})"]}


def build_graph():
    g = StateGraph(CreditState)
    g.add_node("ingest", ingest)
    g.add_node("incomplete", incomplete)
    g.add_node("extract", extract_node)
    g.add_node("detect_discrepancies", detect_discrepancies)
    g.add_node("analyze", analyze)
    g.add_node("policy_check", policy_check)
    g.add_node("risk_grade", risk_grade)
    g.add_node("decide", decide)
    g.add_node("write_memo", write_memo)

    g.add_edge(START, "ingest")
    g.add_conditional_edges("ingest", route_after_ingest, {"extract": "extract", "incomplete": "incomplete"})
    g.add_edge("incomplete", END)
    for a, b in [("extract", "detect_discrepancies"), ("detect_discrepancies", "analyze"),
                 ("analyze", "policy_check"), ("policy_check", "risk_grade"),
                 ("risk_grade", "decide"), ("decide", "write_memo"), ("write_memo", END)]:
        g.add_edge(a, b)
    return g.compile()


def run(case_dir: str) -> CreditState:
    return build_graph().invoke({"case_dir": str(case_dir), "trace": []})
