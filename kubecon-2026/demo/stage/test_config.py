from pathlib import Path

import pytest

import config


def test_missing_required_names_are_reported(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("LLM_BASE_URL=https://example.invalid/openai/v1\n")
    monkeypatch.setattr(config, "ENV_FILE", env_file)
    with pytest.raises(ValueError, match="LLM_API_KEY, LLM_MODEL"):
        config.load_config()


def test_stage_configuration_ignores_shell_and_preserves_literal_key(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("LLM_BASE_URL=https://example.invalid/openai/v1\nLLM_API_KEY='${EXTERNAL}'\nLLM_MODEL=deployment\n")
    monkeypatch.setattr(config, "ENV_FILE", env_file)
    monkeypatch.setenv("EXTERNAL", "should-not-be-used")
    monkeypatch.setenv("LLM_MODEL", "should-not-be-used")
    values = config.load_config()
    assert values["LLM_API_KEY"] == "${EXTERNAL}"
    assert values["LLM_MODEL"] == "deployment"
    assert values["HINDSIGHT_API_LLM_TEMPERATURE"] == "none"


def test_data_directory_must_stay_inside_stage(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("LLM_BASE_URL=https://example.invalid/openai/v1\nLLM_API_KEY=example\nLLM_MODEL=deployment\nHINDSIGHT_DATA_DIR=../outside\n")
    monkeypatch.setattr(config, "ENV_FILE", env_file)
    with pytest.raises(ValueError, match="inside demo/stage"):
        config.load_config()


def test_environment_has_only_explicit_settings(monkeypatch):
    monkeypatch.setenv("SOME_OUTSIDE_TOKEN", "should-not-be-used")
    values = {**config.DEFAULTS, "HINDSIGHT_DATA_DIR": str(config.ROOT / ".hindsight-data")}
    environment = config.isolated_environment(values)
    assert "SOME_OUTSIDE_TOKEN" not in environment
    assert environment["HF_HUB_OFFLINE"] == "1"
    assert environment["TRANSFORMERS_OFFLINE"] == "1"
    assert Path(environment["HOME"]).is_relative_to(config.ROOT)
