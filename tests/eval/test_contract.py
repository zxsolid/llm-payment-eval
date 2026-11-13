"""Ответ модели должен разбираться по схеме. Иначе дальше по цепочке всё ломается."""

import pytest

from conftest import CASES


@pytest.mark.parametrize("case_id", [c["id"] for c in CASES])
def test_response_matches_schema(results, case_id):
    r = results[case_id]
    assert r.ok, f"{case_id}: {r.error}\nответ модели: {r.raw[:300]}"
