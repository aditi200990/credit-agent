import shutil
from pathlib import Path

import pytest

from credit_agent import run
from credit_agent.analysis import emi
from credit_agent.extract import to_number
from credit_agent.fmt import inr
from credit_agent.memo import ungrounded_numbers

DATA = Path(__file__).resolve().parent.parent / "data" / "applications"


@pytest.mark.parametrize("case, decision", [
    ("clean_salaried", "APPROVE"),
    ("income_mismatch", "REFER"),
    ("high_risk_self_employed", "DECLINE"),
])
def test_end_to_end_decisions(case, decision):
    assert run(DATA / case)["decision"] == decision


def test_mismatch_case_flags_the_right_issues():
    codes = {d["code"] for d in run(DATA / "income_mismatch")["discrepancies"]}
    assert codes == {"EMPLOYER_MISMATCH_BANK", "INCOME_MISMATCH_BANK", "UNDISCLOSED_OBLIGATION"}


def test_underwrites_on_lowest_verified_income():
    m = run(DATA / "income_mismatch")["metrics"]
    assert m["assessed_monthly_income"] == 92000      # bank credits, not the declared 1,50,000
    assert m["existing_emi"] == 27500                  # includes the EMI missing from the bureau


def test_missing_document_short_circuits(tmp_path):
    case = tmp_path / "no_payslip"
    shutil.copytree(DATA / "clean_salaried", case)
    (case / "payslip.txt").unlink()
    state = run(case)
    assert state["decision"] == "INCOMPLETE"
    assert "extract" not in " ".join(state["trace"])   # pipeline stopped early


def test_emi_formula():
    assert round(emi(800000, 12.0, 48)) == 21067


def test_indian_number_parsing_and_formatting():
    assert to_number("1,52,000") == 152000
    assert inr(1200000) == "₹12,00,000"
    assert inr(950) == "₹950"


def test_grounding_check_catches_invented_figures():
    facts = {"metrics": {"assessed_monthly_income": 120000, "foir": 0.276}}
    assert not ungrounded_numbers("Income of ₹1,20,000 gives FOIR of 27.6%.", facts)
    assert ungrounded_numbers("Income of ₹1,45,000 gives FOIR of 27.6%.", facts) == {145000.0}


def _fake_llm(monkeypatch, reply):
    from credit_agent import llm
    monkeypatch.setattr(llm, "is_configured", lambda: True)
    monkeypatch.setattr(llm, "chat", lambda system, user: reply)


def test_llm_commentary_used_when_grounded(monkeypatch):
    _fake_llm(monkeypatch, "Assessed income of ₹1,20,000 supports a FOIR of 27.6%; recommend approval.")
    state = run(DATA / "clean_salaried")
    assert state["memo_source"] == "llm"
    assert "recommend approval" in state["memo"]


def test_llm_commentary_rejected_when_it_invents_numbers(monkeypatch):
    _fake_llm(monkeypatch, "Income of ₹1,85,000 easily supports this loan.")   # 1,85,000 is not in the file
    state = run(DATA / "clean_salaried")
    assert state["memo_source"] == "llm_rejected"
    assert "185000" in state["memo"] and "easily supports" not in state["memo"]
