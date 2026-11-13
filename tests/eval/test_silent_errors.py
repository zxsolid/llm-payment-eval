"""Проверка кодом после модели: сколько ошибок она ловит и сколько пропускает."""

import tomllib

from conftest import BY_ID
from payeval.dataset import ROOT
from payeval.guards import review

GATE = tomllib.loads((ROOT / "quality_gate.toml").read_text(encoding="utf-8"))


def test_silent_errors_within_limit(scored, flags):
    r = review([(BY_ID[cid], st, flags[cid]) for cid, st in scored.items()])
    limit = GATE["limits"]["max_silent_errors"]
    assert len(r["silent"]) <= limit, (
        f"ошибок в сумме, валюте, типе операции или дате, которые проверка не заметила: "
        f"{len(r['silent'])} (можно {limit}): {', '.join(r['silent'])}"
    )

