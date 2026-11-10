from config import DEFAULTS, ROOT
from server import redact, server_environment
from model_cache import MODELS, missing_models


def test_server_maps_llm_settings_once_and_ignores_external_environment(monkeypatch):
    monkeypatch.setenv("HINDSIGHT_API_LLM_MODEL", "external-model")
    values = {**DEFAULTS, "HINDSIGHT_DATA_DIR": str(ROOT / ".hindsight-data"),
              "LLM_API_KEY": "test-key", "LLM_BASE_URL": "https://example.invalid/v1",
              "LLM_MODEL": "configured-model"}
    environment = server_environment(values)
    assert environment["HINDSIGHT_API_LLM_API_KEY"] == values["LLM_API_KEY"]
    assert environment["HINDSIGHT_API_LLM_BASE_URL"] == values["LLM_BASE_URL"]
    assert environment["HINDSIGHT_API_LLM_MODEL"] == values["LLM_MODEL"]


def test_server_redacts_credentials_in_output():
    assert redact("token=test-key postgres://user:password@localhost/db", "test-key") == (
        "token=[REDACTED] postgres://[REDACTED]@localhost/db"
    )


def test_missing_model_cache_is_reported_without_network(tmp_path):
    assert set(missing_models(tmp_path)) == set(MODELS)


def test_complete_model_cache_is_accepted(tmp_path):
    for model, files in MODELS.items():
        repo = tmp_path / "hub" / ("models--" + model.replace("/", "--"))
        (repo / "refs").mkdir(parents=True)
        (repo / "refs/main").write_text("revision")
        for name in files:
            path = repo / "snapshots/revision" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("test cache file")
    assert missing_models(tmp_path) == []
