"""Export real per-node outputs and code excerpts used by docs/index.html.

    python docs/build_walkthrough_data.py docs/walkthrough_data.json
"""
import inspect, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from credit_agent import graph, checks, analysis, extract, memo, documents

OUT = Path(sys.argv[1])
DATA = ROOT / "data" / "applications"

def excerpt(fn, start, end=None):
    src = inspect.getsource(fn).splitlines()
    i = next(k for k, l in enumerate(src) if start in l)
    j = next((k for k, l in enumerate(src[i+1:], i+1) if end and end in l), len(src)) if end else len(src)
    return "\n".join(src[i:j]).rstrip()

import textwrap
def ded(s): return textwrap.dedent(s)

code = {
 "ingest": inspect.getsource(graph.ingest) + "\n\n" + inspect.getsource(graph.route_after_ingest),
 "extract": ded(excerpt(extract.extract_payslip, "def extract_payslip")) + "\n\n\n" + ded(excerpt(extract.extract_bank_statement, "salary_credits =", "emi_by_payee")),
 "detect_discrepancies": ded(excerpt(checks.find_discrepancies, "# 3. Income", "# 4.")) + "\n" + ded(excerpt(checks.find_discrepancies, "# 4. Obligations", "return out")),
 "analyze": ded(excerpt(analysis.compute_metrics, "income_sources = {", "return {")) + "\nreturn {..., \"foir\": round((existing_emi + proposed_emi) / assessed_income, 3)}",
 "policy_check": ded(excerpt(analysis.check_policy, "rules = [", "return [")),
 "risk_grade": ded(excerpt(analysis.risk_grade, "points = 100", "return grade")),
 "decide": inspect.getsource(analysis.decide),
 "write_memo": ded(excerpt(memo.build_memo, "source, commentary = ", "src = m")) ,
 "graph": ded(excerpt(graph.build_graph, "g = StateGraph")),
}
code["ingest"] = code["ingest"].strip()

def slim(node, upd):
    u = dict(upd)
    if "documents" in u:
        u["documents"] = {k: ("<%d rows>" % len(v) if isinstance(v, list) else "<text>" if isinstance(v, str) else "<json>") for k, v in u["documents"].items()}
    if "extracted" in u:
        e = json.loads(json.dumps(u["extracted"]))
        e["application"] = {"application_id": e["application"]["application_id"], "declared_monthly_income": e["application"]["declared_monthly_income"], "loan": e["application"]["loan"], "applicant": e["application"]["applicant"]}
        u["extracted"] = e
    return u

cases = {}
for case in ["clean_salaried", "income_mismatch", "high_risk_self_employed"]:
    steps = []
    for chunk in graph.build_graph().stream({"case_dir": str(DATA / case), "trace": []}, stream_mode="updates"):
        for node, upd in chunk.items():
            steps.append({"node": node, "update": slim(node, upd)})
    cases[case] = steps

docs = {}
for case in cases:
    d = DATA / case
    docs[case] = {f.name: f.read_text() for f in sorted(d.iterdir())}

OUT.write_text(json.dumps({"code": code, "cases": cases, "docs": docs}, ensure_ascii=False, indent=1))
print({c: [s["node"] for s in v] for c, v in cases.items()})
for k, v in code.items(): print("==", k, len(v.splitlines()), "lines")
