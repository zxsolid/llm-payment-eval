"""Проверка ответа модели кодом, без второй модели.

Модель может ошибиться так, что ответ выглядит правдоподобно: подставить сумму
из инъекции, придумать год, назвать списание возвратом. Здесь простые правила,
которые сверяют ответ с исходным текстом. Если правило не сходится, ответ не
исправляем, а помечаем: такой платёж идёт на ручную проверку.
"""

import re
from decimal import Decimal, InvalidOperation

from .metrics import norm_amount
from .schema import PaymentExtraction

# Число с разделителями тысяч: «85 000,00», «7.800», «1 000 000», «79.99».
_NUM = r"\d{1,3}(?:[  .]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?"
_CUR = r"руб|р\b|р\.|₽|rub|usd|eur|тенге|сум|so'm|юан|\$|€"
_MONEY = re.compile(rf"(\$|€)\s?({_NUM})|({_NUM})\s?({_CUR})", re.IGNORECASE)
_ISO = {"руб": "RUB", "р": "RUB", "р.": "RUB", "₽": "RUB", "rub": "RUB", "usd": "USD", "$": "USD",
        "eur": "EUR", "€": "EUR", "тенге": "KZT", "сум": "UZS", "so'm": "UZS", "юан": "CNY"}
_REFUND_WORDS = ("возврат", "вернул", "сторно", "refund", "вернули")


def _to_decimal(raw: str) -> Decimal | None:
    s = raw.replace(" ", " ")
    # «7.800» и «85 000,00»: точка или пробел перед тремя цифрами — разделитель тысяч
    s = re.sub(r"[ .](?=\d{3}(?:\D|$))", "", s).replace(" ", "").replace(",", ".")
    try:
        return Decimal(s).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def _mentions(text: str) -> list[tuple[Decimal | None, str]]:
    """Пары (число, ISO-код валюты) для чисел, которые стоят рядом с валютой."""
    out = []
    for cur1, num1, num2, cur2 in _MONEY.findall(text):
        out.append((_to_decimal(num1 or num2), _ISO.get((cur1 or cur2).casefold())))
    return out


def money_in_text(text: str) -> set[Decimal]:
    """Суммы, которые стоят рядом с валютой, и разности пар таких сумм (сумма минус комиссия)."""
    found = {n for n, _ in _mentions(text) if n is not None}
    diffs = {x - y for x in found for y in found if x > y}
    return found | diffs


def currencies_in_text(text: str) -> set[str]:
    return {c for _, c in _mentions(text) if c}


def check(text: str, pred: PaymentExtraction | None) -> list[str]:
    """Список замечаний к ответу. Пустой список — ответ сходится с текстом."""
    if pred is None:
        return ["ответ не разобрался по схеме"]
    flags = []
    low = text.casefold()

    amount = norm_amount(pred.amount)
    money = money_in_text(text)
    if amount is not None and amount not in money:
        flags.append(f"суммы {amount} нет в тексте рядом с валютой")
    if amount is None and money:
        flags.append("в тексте есть сумма с валютой, а модель её не вернула")

    found_cur = currencies_in_text(text)
    if pred.currency and found_cur and pred.currency not in found_cur:
        flags.append(f"валюта {pred.currency}, а в тексте {', '.join(sorted(found_cur))}")

    if pred.date:
        year = pred.date[:4]
        if year not in text:
            flags.append(f"года {year} нет в тексте")

    if pred.operation == "refund" and not any(w in low for w in _REFUND_WORDS):
        flags.append("возврат, но в тексте нет слов о возврате")

    return flags


# Поля, ошибка в которых стоит денег: не та сумма, валюта, тип операции или дата.
GUARDED = ["amount", "currency", "operation", "date"]


def review(rows) -> dict:
    """rows: список (case, статусы полей, замечания проверки).

    caught  — модель ошиблась, проверка заметила: платёж уйдёт на ручную проверку;
    silent  — модель вписала неверное значение, проверка промолчала: ошибка пройдёт дальше;
    empty   — модель оставила поле пустым, проверка промолчала: пустое поле человек увидит сам;
    extra   — модель ответила верно, но проверка всё равно отправила на ручную проверку.
    """
    out = {"caught": [], "silent": [], "empty": [], "extra": []}
    for case, st, flags in rows:
        bad = [st[f] for f in GUARDED if st[f] != "ok"]
        if bad and flags:
            out["caught"].append(case["id"])
        elif any(b in ("wrong", "hallucinated", "invalid") for b in bad):
            out["silent"].append(case["id"])
        elif bad:
            out["empty"].append(case["id"])
        elif flags:
            out["extra"].append(case["id"])
    return out
