"""Общие данные для проверок модели.

Ответы модели берутся из cassettes/ (PAYEVAL_MODE=replay, по умолчанию)
или запрашиваются у Ollama (PAYEVAL_MODE=live / record).
Промт выбирается через PAYEVAL_PROMPT, по умолчанию v3_example.
"""

import os

import pytest

from payeval.client import CassetteMissing, CassetteStale, Settings
from payeval.dataset import load_cases
from payeval.extractor import extract
from payeval.metrics import score_case

CASES = load_cases()
BY_ID = {c["id"]: c for c in CASES}


@pytest.fixture(scope="session")
def prompt_name() -> str:
    return os.getenv("PAYEVAL_PROMPT", "v3_example")


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings()


@pytest.fixture(scope="session")
def results(prompt_name, settings):
    out = {}
    try:
        for c in CASES:
            out[c["id"]] = extract(c, prompt_name, settings=settings)
    except CassetteMissing as e:
        pytest.skip(f"нет записанных ответов модели ({e}). Запустите: make record")
    except CassetteStale as e:
        pytest.fail(str(e))
    return out


@pytest.fixture(scope="session")
def scored(results):
    return {cid: score_case(BY_ID[cid]["expected"], r.parsed) for cid, r in results.items()}


def ids_of(category: str) -> list[str]:
    return [c["id"] for c in CASES if c["category"] == category]


@pytest.fixture(scope="session")
def flags(results):
    from payeval.guards import check

    return {cid: check(BY_ID[cid]["text"], r.parsed) for cid, r in results.items()}


def model_or_guard(model_ok: bool, flags: list[str], what: str) -> None:
    """Проверяем систему целиком: модель плюс проверку кодом.

    Если модель не ошиблась, тест зелёный. Если ошиблась, но guards.py это заметил,
    тест тоже зелёный: платёж уйдёт на ручную проверку. В выводе pytest останется
    предупреждение, чтобы слабое место модели не потерялось. Красный тест — только
    когда ошибку не заметил никто.
    """
    import warnings

    if model_ok:
        return
    assert flags, f"{what}, и проверка кодом это пропустила"
    warnings.warn(f"{what}; поймала проверка кодом: {'; '.join(flags)}", stacklevel=2)
