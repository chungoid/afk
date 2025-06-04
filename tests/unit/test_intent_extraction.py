import pytest
from pathlib import Path
from types import SimpleNamespace
import openai
from analysis_agent.prompt_steps.intent_extraction import run, IntentExtractionError

class DummyChoice:
    def __init__(self, content):
        self.message = SimpleNamespace(content=content)

class DummyResponse:
    def __init__(self, content):
        self.choices = [DummyChoice(content)]

def test_run_success(monkeypatch, tmp_path):
    templates_dir = tmp_path
    template_file = templates_dir / "01_intent_extraction.jinja2"
    template_file.write_text("Extract intent from: {{ text }}")
    def fake_create(model, messages, temperature):
        assert isinstance(model, str)
        assert messages[-1]["content"] == "Extract intent from: hello world"
        return DummyResponse('{"intent": "greet"}')
    monkeypatch.setattr(openai.ChatCompletion, "create", staticmethod(fake_create))
    result = run({"text": "hello world"}, templates_dir)
    assert result == {"intent": "greet"}

def test_run_invalid_json(monkeypatch, tmp_path):
    templates_dir = tmp_path
    (templates_dir / "01_intent_extraction.jinja2").write_text("dummy template")
    monkeypatch.setattr(openai.ChatCompletion, "create", staticmethod(lambda *args, **kwargs: DummyResponse("not a json")))
    with pytest.raises(IntentExtractionError):
        run({}, templates_dir)

def test_run_missing_intent_key(monkeypatch, tmp_path):
    templates_dir = tmp_path
    (templates_dir / "01_intent_extraction.jinja2").write_text("dummy")
    monkeypatch.setattr(openai.ChatCompletion, "create", staticmethod(lambda *args, **kwargs: DummyResponse('{"no_intent":"oops"}')))
    with pytest.raises(IntentExtractionError):
        run({}, templates_dir)

def test_missing_template_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        run({"text": "anything"}, tmp_path)