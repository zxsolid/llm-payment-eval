"""Проверяем сам харнесс, без модели. Эти тесты всегда идут в CI."""

from payeval.extractor import parse
from payeval.metrics import norm_amount, norm_text, score_case, summarize
from payeval.schema import PaymentExtraction

EXP = {
    "amount": "15000.00", "currency": "RUB", "counterparty": "ООО Ромашка",
    "purpose_keywords": ["аренд"], "invoice_number": "12", "date": "2026-10-05", "operation": "payment",
}


def pred(**kw):
    base = dict(amount="15000.00", currency="RUB", counterparty="ООО «Ромашка»", purpose="Аренда офиса",
                invoice_number="№12", date="2026-10-05", operation="payment")
    base.update(kw)
    return PaymentExtraction(**base)


def test_all_ok_with_normalization():
    assert set(score_case(EXP, pred(amount="15 000,00")).values()) == {"ok"}


def test_amount_formats():
    assert norm_amount("15000") == norm_amount("15 000,00") == norm_amount("15000.00")
    assert norm_amount("сто") is None


def test_text_normalization():
    assert norm_text("ООО «Ёлка»") == norm_text('ооо "елка"')


def test_wrong_and_missed():
    st = score_case(EXP, pred(amount="1500.00", date=None, purpose="цветы"))
    assert st["amount"] == "wrong"
    assert st["date"] == "missed"
    assert st["purpose"] == "wrong"


def test_hallucination_detected():
    exp = dict(EXP, amount=None, currency=None, date=None)
    st = score_case(exp, pred())
    assert st["amount"] == st["currency"] == st["date"] == "hallucinated"


def test_operation():
    assert score_case(EXP, pred(operation="refund"))["operation"] == "wrong"


def test_invalid_response():
    p, err = parse("Вот ваш JSON: {")
    assert p is None and "JSON" in err
    p, err = parse('{"amount": "1", "operation": "maybe"}')
    assert p is None and "схеме" in err
    assert set(score_case(EXP, None).values()) == {"invalid"}


def test_summary():
    case = {"category": "clean", "expected": EXP}
    s = summarize([(case, score_case(EXP, pred())), (case, score_case(EXP, None))])
    assert s["accuracy"]["amount"] == 0.5
    assert s["valid_json_rate"] == 0.5
    assert s["by_category"]["clean"] == {"total": 2, "critical_ok": 1}
