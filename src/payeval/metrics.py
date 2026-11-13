"""Сравнение ответа модели с эталоном по каждому полю.

Статусы поля:
- ok           — совпало (или оба пустые);
- wrong        — оба заполнены, но значения разные;
- hallucinated — в эталоне пусто, а модель что-то вписала;
- missed       — в эталоне есть значение, а модель вернула пусто.
"""

import re
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from typing import Optional

from .schema import PaymentExtraction

FIELDS = ["amount", "currency", "counterparty", "purpose", "invoice_number", "date", "operation"]
CRITICAL = ["amount", "currency", "operation"]


def norm_amount(v: Optional[str]) -> Optional[Decimal]:
    if v is None:
        return None
    s = str(v).replace(" ", "").replace(" ", "").replace(",", ".")
    try:
        return Decimal(s).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def norm_text(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    s = v.casefold().replace("ё", "е")
    s = re.sub(r"[«»\"'“”„]", "", s)
    s = re.sub(r"[.,]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s or None


def norm_invoice(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    s = v.replace("№", "").strip().casefold()
    return s or None


def keyword_found(keyword: str, text: str) -> bool:
    """Ключевое слово назначения. Варианты через «|»: «доставк|доствк» — подходит любой."""
    return any(alt.casefold().replace("ё", "е") in text for alt in keyword.split("|"))


def _status(expected, actual) -> str:
    if expected is None and actual is None:
        return "ok"
    if expected is None:
        return "hallucinated"
    if actual is None:
        return "missed"
    return "ok" if expected == actual else "wrong"


def score_case(expected: dict, pred: Optional[PaymentExtraction]) -> dict[str, str]:
    """Возвращает статус по каждому полю. Если ответ не разобрался, все поля — invalid."""
    if pred is None:
        return {f: "invalid" for f in FIELDS}

    out = {
        "amount": _status(norm_amount(expected["amount"]), norm_amount(pred.amount)),
        "currency": _status(expected["currency"], pred.currency),
        "counterparty": _status(norm_text(expected["counterparty"]), norm_text(pred.counterparty)),
        "invoice_number": _status(norm_invoice(expected["invoice_number"]), norm_invoice(pred.invoice_number)),
        "date": _status(expected["date"], pred.date),
        "operation": "ok" if expected["operation"] == pred.operation else "wrong",
    }

    kws = expected.get("purpose_keywords") or []
    purpose = norm_text(pred.purpose) or ""
    if not kws:
        out["purpose"] = "ok"
    elif not purpose:
        out["purpose"] = "missed"
    else:
        out["purpose"] = "ok" if all(keyword_found(k, purpose) for k in kws) else "wrong"
    return out


def summarize(scored: list[tuple[dict, dict]]) -> dict:
    """scored: список (case, статусы). Возвращает долю ok по полям, по категориям и счётчики ошибок."""
    by_field = {f: Counter() for f in FIELDS}
    by_category = defaultdict(lambda: Counter())
    for case, st in scored:
        for f, s in st.items():
            by_field[f][s] += 1
        crit_ok = all(st[f] == "ok" for f in CRITICAL)
        by_category[case["category"]]["total"] += 1
        by_category[case["category"]]["critical_ok"] += int(crit_ok)

    n = len(scored) or 1
    accuracy = {f: by_field[f]["ok"] / n for f in FIELDS}
    hallucination_rate = {f: by_field[f]["hallucinated"] / n for f in FIELDS}
    return {
        "n": len(scored),
        "accuracy": accuracy,
        "hallucination_rate": hallucination_rate,
        "counts": {f: dict(c) for f, c in by_field.items()},
        "by_category": {k: dict(v) for k, v in sorted(by_category.items())},
        "valid_json_rate": 1 - by_field["amount"]["invalid"] / n,
    }
