"""Load only the stage-local .env; never consult the caller's configuration."""

from pathlib import Path
from urllib.parse import urlparse

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
REQUIRED = ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL")
DEFAULTS = {
    "HINDSIGHT_API_LLM_PROVIDER": "openai-responses",
    "HINDSIGHT_API_LLM_TEMPERATURE": "none",
    "HINDSIGHT_PORT": "8888",
    "HINDSIGHT_CP_PORT": "9999",
    "HINDSIGHT_DATA_DIR": "./.hindsight-data",
    "APP_PORT": "8000",
}


def load_config():
    if not ENV_FILE.is_file():
        raise ValueError("Missing demo/stage/.env; copy .env.example and fill in required values")
    raw = dotenv_values(ENV_FILE, interpolate=False)
    missing = [name for name in REQUIRED if not (raw.get(name) or "").strip()]
    if missing:
        raise ValueError("Missing required variable(s) in demo/stage/.env: " + ", ".join(missing))
    values = {name: raw[name].strip() for name in REQUIRED}
    values.update({name: (raw.get(name) or "").strip() or default for name, default in DEFAULTS.items()})
    url = urlparse(values["LLM_BASE_URL"])
    if (url.scheme not in ("http", "https") or not url.netloc or url.username or url.password
            or url.query or url.fragment or url.path.rstrip("/").endswith("/responses")):
        raise ValueError("LLM_BASE_URL must be an HTTP(S) base URL without a /responses suffix")
    for name in ("HINDSIGHT_PORT", "HINDSIGHT_CP_PORT", "APP_PORT"):
        if not values[name].isdigit() or not 1 <= int(values[name]) <= 65535:
            raise ValueError(f"{name} must be a port number from 1 to 65535")
    data = (ROOT / values["HINDSIGHT_DATA_DIR"]).resolve()
    if data == ROOT or not data.is_relative_to(ROOT):
        raise ValueError("HINDSIGHT_DATA_DIR must be a directory inside demo/stage")
    values["HINDSIGHT_DATA_DIR"] = str(data)
    return values


def isolated_environment(config):
    """Construct an environment without inherited credentials or profile settings."""
    home = Path(config["HINDSIGHT_DATA_DIR"])
    cache = ROOT / ".cache"
    temporary = cache / "tmp"
    for directory in (home, cache, temporary):
        directory.mkdir(parents=True, exist_ok=True)
    return {
        **config,
        "HOME": str(home),
        "PATH": f"{ROOT / '.venv/bin'}:{ROOT / '.local/bin'}:/usr/bin:/bin:/usr/sbin:/sbin",
        "XDG_CACHE_HOME": str(cache),
        "XDG_CONFIG_HOME": str(ROOT / ".config"),
        "HF_HOME": str(cache / "huggingface"),
        "HUGGINGFACE_HUB_CACHE": str(cache / "huggingface/hub"),
        # Stage startup must use the prewarmed local model cache.
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        # Xet download retries stalled on this network; use the standard HTTPS path.
        "HF_HUB_DISABLE_XET": "1",
        "NEXT_TELEMETRY_DISABLED": "1",
        "TORCH_HOME": str(cache / "torch"),
        "TMPDIR": str(temporary),
        "PYTHONNOUSERSITE": "1",
        "PYTHONUNBUFFERED": "1",
    }
