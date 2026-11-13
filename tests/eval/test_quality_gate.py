"""Гейт качества: доля верных полей по всему набору не ниже порогов из quality_gate.toml."""

import tomllib

from conftest import BY_ID
from payeval.dataset import ROOT
from payeval.metrics import summarize

GATE = tomllib.loads((ROOT / "quality_gate.toml").read_text(encoding="utf-8"))


def test_quality_gate(scored):
    s = summarize([(BY_ID[cid], st) for cid, st in scored.items()])
    problems = []
    for field, minimum in GATE["accuracy"].items():
        if s["accuracy"][field] < minimum:
            problems.append(f"{field}: {s['accuracy'][field]:.0%} < {minimum:.0%}")
    if s["valid_json_rate"] < GATE["limits"]["valid_json_rate"]:
        problems.append(f"валидный JSON: {s['valid_json_rate']:.0%}")
    halluc = s["counts"]["amount"].get("hallucinated", 0)
    if halluc > GATE["limits"]["max_amount_hallucinations"]:
        problems.append(f"выдуманных сумм: {halluc}")
    assert not problems, "Гейт не пройден:\n" + "\n".join(problems)
