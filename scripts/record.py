"""Прогоняет набор через Ollama и записывает ответы в cassettes/.

    python scripts/record.py                      # оба промта, по одному прогону
    python scripts/record.py --consistency        # плюс 3 повтора для теста повторяемости
    PAYEVAL_MODEL=qwen3:14b python scripts/record.py
"""

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from payeval.client import Settings  # noqa: E402
from payeval.dataset import load_cases  # noqa: E402
from payeval.extractor import extract  # noqa: E402

PROMPTS = ["v1_naive", "v2_rules", "v3_example"]
CONSISTENCY_SAMPLE = ["p017", "p019", "p025", "p040", "p042", "p048", "p058"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", nargs="+", default=PROMPTS)
    ap.add_argument("--consistency", action="store_true", help="3 повтора выборки для теста повторяемости")
    args = ap.parse_args()

    os.environ["PAYEVAL_MODE"] = "record"
    s = Settings()
    cases = load_cases()
    print(f"модель {s.model}, {len(cases)} кейсов, промты: {', '.join(args.prompts)}")

    for prompt in args.prompts:
        t0, bad = time.time(), 0
        for i, c in enumerate(cases, 1):
            r = extract(c, prompt, settings=s)
            bad += not r.ok
            print(f"\r{prompt}: {i}/{len(cases)}", end="", flush=True)
        print(f"  готово за {time.time() - t0:.0f} с, не по схеме: {bad}")

        if args.consistency:
            by_id = {c["id"]: c for c in cases}
            for run in (1, 2, 3):
                for cid in CONSISTENCY_SAMPLE:
                    extract(by_id[cid], prompt, run=run, settings=s)
            print(f"{prompt}: повторы записаны")


if __name__ == "__main__":
    main()
