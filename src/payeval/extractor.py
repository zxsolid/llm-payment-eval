import json
from dataclasses import dataclass, field
from typing import Optional

from pydantic import ValidationError

from .client import Settings, complete
from .dataset import ROOT
from .schema import PaymentExtraction

PROMPTS = ROOT / "prompts"
SCHEMA = PaymentExtraction.model_json_schema()


def load_prompt(name: str) -> str:
    return (PROMPTS / f"{name}.txt").read_text(encoding="utf-8")


@dataclass
class Result:
    case_id: str
    raw: str
    parsed: Optional[PaymentExtraction] = None
    error: Optional[str] = None
    extra: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.parsed is not None


def parse(raw: str) -> tuple[Optional[PaymentExtraction], Optional[str]]:
    try:
        return PaymentExtraction.model_validate(json.loads(raw)), None
    except json.JSONDecodeError as e:
        return None, f"не JSON: {e}"
    except ValidationError as e:
        return None, f"не по схеме: {e.errors()[0]['msg']}"


def extract(case: dict, prompt_name: str, run: int = 0, settings: Settings | None = None) -> Result:
    raw = complete(case["id"], prompt_name, load_prompt(prompt_name), case["text"], SCHEMA, run, settings)
    parsed, error = parse(raw)
    return Result(case["id"], raw, parsed, error)
