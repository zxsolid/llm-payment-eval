from payeval.dataset import load_cases
from payeval.metrics import keyword_found, norm_text
from payeval.schema import PaymentExtraction


def test_dataset_is_consistent():
    cases = load_cases()
    assert len(cases) >= 50
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids))
    for c in cases:
        e = c["expected"]
        # эталон сам должен проходить схему, иначе мы проверяем модель против кривой разметки
        PaymentExtraction(
            amount=e["amount"], currency=e["currency"], counterparty=e["counterparty"], purpose="x",
            invoice_number=e["invoice_number"], date=e["date"], operation=e["operation"],
        )
        assert (e["amount"] is None) == (e["currency"] is None), c["id"]


def test_purpose_keywords_come_from_text():
    # Правило для модели: назначение словами из текста. Значит, хотя бы один вариант
    # каждого ключевого слова должен встречаться в самом сообщении.
    for c in load_cases():
        text = norm_text(c["text"]) or ""
        for kw in c["expected"]["purpose_keywords"]:
            assert keyword_found(kw, text), f"{c['id']}: ключевого слова «{kw}» нет в тексте"
