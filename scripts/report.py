"""Строит reports/report.md: сравнение промтов по полям, категориям и список ошибок."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from payeval.client import CassetteMissing, CassetteStale, Settings  # noqa: E402
from payeval.dataset import ROOT, load_cases  # noqa: E402
from payeval.extractor import extract  # noqa: E402
from payeval.guards import GUARDED, check, review  # noqa: E402
from payeval.metrics import CRITICAL, FIELDS, score_case, summarize  # noqa: E402

PROMPTS = ["v1_naive", "v2_rules", "v3_example"]
NAMES = {
    "amount": "сумма", "currency": "валюта", "counterparty": "контрагент", "purpose": "назначение",
    "invoice_number": "номер счёта", "date": "дата", "operation": "оплата/возврат",
}


def run(prompt: str, s: Settings):
    cases = load_cases()
    scored, results = [], {}
    for c in cases:
        r = extract(c, prompt, settings=s)
        results[c["id"]] = r
        scored.append((c, score_case(c["expected"], r.parsed)))
    return scored, results


def pct(x: float) -> str:
    return f"{x:.0%}"


def main() -> None:
    os.environ.setdefault("PAYEVAL_MODE", "replay")
    s = Settings()
    data = {}
    for p in PROMPTS:
        try:
            data[p] = run(p, s)
        except (CassetteMissing, CassetteStale) as e:
            print(f"пропускаю {p}: {e}")
    if not data:
        sys.exit("Нет записанных ответов. Сначала: make record")

    sums = {p: summarize(sc) for p, (sc, _) in data.items()}
    ps = list(data)
    lines = [f"# Отчёт: модель `{s.model}`, {sums[ps[0]]['n']} сообщений", ""]

    lines += ["## Доля верных полей", "", "| Поле | " + " | ".join(ps) + " |", "|---|" + "---|" * len(ps)]
    for f in FIELDS:
        lines.append(f"| {NAMES[f]} | " + " | ".join(pct(sums[p]["accuracy"][f]) for p in ps) + " |")
    lines.append("| ответ по схеме | " + " | ".join(pct(sums[p]["valid_json_rate"]) for p in ps) + " |")
    lines.append("| выдуманные суммы | " + " | ".join(
        str(sums[p]["counts"]["amount"].get("hallucinated", 0)) for p in ps) + " |")
    lines.append("| выдуманные даты | " + " | ".join(
        str(sums[p]["counts"]["date"].get("hallucinated", 0)) for p in ps) + " |")

    lines += ["", "## Ключевые поля по категориям", "",
              f"Кейс верный, если совпали {', '.join(NAMES[f] for f in CRITICAL)}.", "",
              "| Категория | " + " | ".join(ps) + " |", "|---|" + "---|" * len(ps)]
    for cat in sums[ps[0]]["by_category"]:
        cells = []
        for p in ps:
            b = sums[p]["by_category"][cat]
            cells.append(f"{b['critical_ok']}/{b['total']}")
        lines.append(f"| {cat} | " + " | ".join(cells) + " |")

    lines += ["", "## Проверка кодом после модели", "",
              f"`guards.py` сверяет ответ с текстом: сумма стоит рядом с валютой, год есть в тексте, "
              f"у возврата есть слова о возврате. Ошибкой считаем неверные: {', '.join(NAMES[f] for f in GUARDED)}.", "",
              "| | " + " | ".join(ps) + " |", "|---|" + "---|" * len(ps)]
    revs = {}
    for p in ps:
        sc, res = data[p]
        revs[p] = review([(c, st, check(c["text"], res[c["id"]].parsed)) for c, st in sc])
    for key, title in (("caught", "ошибка, проверка поймала"), ("silent", "неверное значение, проверка пропустила"),
                       ("empty", "пустое поле, проверка промолчала"),
                       ("extra", "ответ верный, но ушёл на ручную проверку")):
        lines.append(f"| {title} | " + " | ".join(str(len(revs[p][key])) for p in ps) + " |")

    last = ps[-1]
    scored, results = data[last]
    if revs[last]["silent"]:
        lines += ["", f"Пропущенные ошибки `{last}`: " + ", ".join(revs[last]["silent"])]
    lines += ["", f"## Ошибки промта `{last}`", ""]
    for c, st in scored:
        bad = {f: v for f, v in st.items() if v != "ok"}
        if not bad:
            continue
        r = results[c["id"]]
        got = r.parsed.model_dump() if r.parsed else r.error
        fl = check(c["text"], r.parsed)
        lines += [f"**{c['id']}** ({c['category']}): " + ", ".join(f"{NAMES[f]} — {v}" for f, v in bad.items()),
                  f"> {c['text']}", "", f"Ответ модели: `{got}`", "",
                  f"Проверка кодом: {'; '.join(fl) if fl else 'замечаний нет'}", ""]

    out = ROOT / "reports" / "report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"отчёт: {out}")


if __name__ == "__main__":
    main()
