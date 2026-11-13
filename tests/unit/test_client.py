import json

import pytest

from payeval import client
from payeval.client import CassetteMissing, CassetteStale, Settings, complete


def test_replay_without_cassette_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(client, "CASSETTES", tmp_path)
    with pytest.raises(CassetteMissing):
        complete("x1", "v2_rules", "sys", "text", {}, settings=Settings(mode="replay", model="m"))


def test_record_then_replay(tmp_path, monkeypatch):
    monkeypatch.setattr(client, "CASSETTES", tmp_path)
    monkeypatch.setattr(client, "_call_ollama", lambda s, sys, text, schema: '{"operation": "payment"}')
    raw = complete("x1", "v2_rules", "sys", "t", {}, settings=Settings(mode="record", model="qwen3:4b"))
    saved = json.loads(next(tmp_path.rglob("x1.json")).read_text(encoding="utf-8"))
    assert saved["raw"] == raw
    again = complete("x1", "v2_rules", "sys", "t", {}, settings=Settings(mode="replay", model="qwen3:4b"))
    assert again == raw


def test_replay_with_changed_prompt_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(client, "CASSETTES", tmp_path)
    monkeypatch.setattr(client, "_call_ollama", lambda s, sys, text, schema: '{"operation": "payment"}')
    complete("x1", "v2_rules", "старый промт", "t", {}, settings=Settings(mode="record", model="m"))
    with pytest.raises(CassetteStale):
        complete("x1", "v2_rules", "новый промт", "t", {}, settings=Settings(mode="replay", model="m"))
