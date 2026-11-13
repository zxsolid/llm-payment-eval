"""Повторяемость: один и тот же текст несколько раз должен давать те же ключевые поля.

Нужны дополнительные прогоны (make record-consistency), иначе тест пропускается.
"""

import pytest

from conftest import BY_ID
from payeval.client import CassetteMissing
from payeval.extractor import extract
from payeval.metrics import CRITICAL

SAMPLE = ["p017", "p019", "p025", "p040", "p042", "p048", "p058"]
RUNS = 3


@pytest.mark.parametrize("case_id", SAMPLE)
def test_same_answer_on_repeat(prompt_name, settings, case_id):
    answers = []
    try:
        for run in range(1, RUNS + 1):
            r = extract(BY_ID[case_id], prompt_name, run=run, settings=settings)
            assert r.ok, r.error
            answers.append(tuple(getattr(r.parsed, f) for f in CRITICAL))
    except CassetteMissing:
        pytest.skip("нет повторных прогонов: make record-consistency")
    assert len(set(answers)) == 1, f"{case_id}: разные ответы на одинаковый вход: {answers}"
