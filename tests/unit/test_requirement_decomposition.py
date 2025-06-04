import pytest
import json
from pathlib import Path
import analysis_agent.prompt_steps.requirement_decomposition as rd

class DummyChoice:
    def __init__(self, content):
        self.message = type("Message", (), {"content": content})

class DummyResponse:
    def __init__(self, content):
        self.choices = [DummyChoice(content)]

def test_run_success(tmp_path, monkeypatch):
    input_data = {"requirement": "Implement login"}
    templates_dir = tmp_path / "prompts"
    templates_dir.mkdir()
    (templates_dir / "02_requirement_decomposition.jinja2").write_text("Prompt: {{ input.requirement }}")
    expected_output = {"decomposed_requirements": ["User must be authenticated"]}
    def fake_create(*args, **kwargs):
        return DummyResponse(json.dumps(expected_output))
    monkeypatch.setattr(rd.openai.ChatCompletion, "create", fake_create)
    result = rd.run(input_data, templates_dir)
    assert result == expected_output

def test_run_invalid_json(tmp_path, monkeypatch):
    input_data = {"requirement": "Implement login"}
    templates_dir = tmp_path / "prompts"
    templates_dir.mkdir()
    (templates_dir / "02_requirement_decomposition.jinja2").write_text("Prompt: {{ input.requirement }}")
    def fake_create(*args, **kwargs):
        return DummyResponse("not a json")
    monkeypatch.setattr(rd.openai.ChatCompletion, "create", fake_create)
    with pytest.raises(ValueError):
        rd.run(input_data, templates_dir)

def test_run_llm_error(tmp_path, monkeypatch):
    input_data = {}
    templates_dir = tmp_path / "prompts"
    templates_dir.mkdir()
    (templates_dir / "02_requirement_decomposition.jinja2").write_text("Template content")
    def fake_create(*args, **kwargs):
        raise RuntimeError("API failure")
    monkeypatch.setattr(rd.openai.ChatCompletion, "create", fake_create)
    with pytest.raises(RuntimeError):
        rd.run(input_data, templates_dir)