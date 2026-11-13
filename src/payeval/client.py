"""Вызов модели с записью ответов в файлы.

Режимы (переменная PAYEVAL_MODE):
- replay  — по умолчанию: берём ответ из cassettes/, модель не нужна. Так работает CI.
- record  — зовём модель и сохраняем ответ в cassettes/.
- live    — зовём модель и ничего не сохраняем.
"""

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .dataset import ROOT

CASSETTES = ROOT / "cassettes"
DEFAULT_MODEL = "qwen3:4b"


class CassetteMissing(Exception):
    pass


class CassetteStale(Exception):
    """Промт поменяли, а ответы модели записаны со старым. Нужно перезаписать."""


def prompt_sha(system: str) -> str:
    return hashlib.sha256(system.encode("utf-8")).hexdigest()[:12]


@dataclass
class Settings:
    mode: str = field(default_factory=lambda: os.getenv("PAYEVAL_MODE", "replay"))
    model: str = field(default_factory=lambda: os.getenv("PAYEVAL_MODEL", DEFAULT_MODEL))
    host: str = field(default_factory=lambda: os.getenv("OLLAMA_HOST", "http://localhost:11434"))


def _slug(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", model)


def cassette_path(model: str, prompt: str, case_id: str, run: int = 0) -> Path:
    suffix = "" if run == 0 else f".run{run}"
    return CASSETTES / _slug(model) / prompt / f"{case_id}{suffix}.json"


def _call_ollama(settings: Settings, system: str, text: str, schema: dict) -> str:
    from ollama import Client  # импорт здесь, чтобы replay работал без ollama

    client = Client(host=settings.host)
    resp = client.chat(
        model=settings.model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": text}],
        format=schema,
        options={"temperature": 0},
        think=False,
    )
    return resp.message.content


def complete(case_id: str, prompt_name: str, system: str, text: str, schema: dict,
             run: int = 0, settings: Settings | None = None) -> str:
    """Возвращает сырой ответ модели (строку) для одного сообщения."""
    s = settings or Settings()
    path = cassette_path(s.model, prompt_name, case_id, run)

    if s.mode == "replay":
        if not path.exists():
            shown = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
            raise CassetteMissing(str(shown))
        data = json.loads(path.read_text(encoding="utf-8"))
        if "prompt_sha" in data and data["prompt_sha"] != prompt_sha(system):
            raise CassetteStale(f"{prompt_name}: промт изменился после записи ответов. Запустите: make record")
        return data["raw"]

    raw = _call_ollama(s, system, text, schema)
    if s.mode == "record":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"model": s.model, "prompt": prompt_name, "prompt_sha": prompt_sha(system),
                        "case": case_id, "run": run, "raw": raw},
                       ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
    return raw
