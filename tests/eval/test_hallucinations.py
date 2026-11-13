"""Модель не должна выдумывать то, чего нет в тексте."""

import pytest

from conftest import BY_ID, CASES, model_or_guard

NO_AMOUNT = [c["id"] for c in CASES if c["expected"]["amount"] is None]
NO_DATE = [c["id"] for c in CASES if c["expected"]["date"] is None]


@pytest.mark.parametrize("case_id", NO_AMOUNT)
def test_no_invented_amount(results, flags, case_id):
    r = results[case_id]
    assert r.ok, r.error
    model_or_guard(r.parsed.amount is None, flags[case_id], f"{case_id}: в тексте нет суммы, модель вписала {r.parsed.amount}")


@pytest.mark.parametrize("case_id", NO_DATE)
def test_no_invented_date(results, flags, case_id):
    r = results[case_id]
    assert r.ok, r.error
    model_or_guard(r.parsed.date is None, flags[case_id],
                   f"{case_id}: даты нет или она без года, модель вписала {r.parsed.date} («{BY_ID[case_id]['text']}»)")
