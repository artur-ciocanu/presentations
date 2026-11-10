#!/usr/bin/env python3
"""Start the isolated native server; only its child receives LLM settings."""
import os
import signal
import socket
import subprocess
import sys
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent
keys = ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL")
with (ROOT.parents[1] / "stage" / ".env").open() as source:
    selected = [line for line in source if line.lstrip().removeprefix("export ").split("=", 1)[0].strip() in keys]
values = dotenv_values(stream=StringIO("\n".join(selected)), interpolate=False)
if any(not values.get(k) for k in keys):
    sys.exit("Missing LLM_BASE_URL, LLM_API_KEY, or LLM_MODEL in stage/.env")
for port in (8890, 55434):
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            sys.exit(f"Required port {port} is not free")
home = ROOT / ".data" / "home"
home.mkdir(parents=True, exist_ok=True)
cache = ROOT / ".cache"
cache.mkdir(exist_ok=True)
env = {k: os.environ[k] for k in ("PATH", "LANG", "LC_ALL", "SSL_CERT_FILE", "SSL_CERT_DIR", "SYSTEMROOT") if k in os.environ}
env.update({
    "HOME": str(home), "PG0_HOME": str(ROOT / ".data" / "pg0"),
    "XDG_CACHE_HOME": str(cache), "HF_HOME": str(cache / "huggingface"),
    "TORCH_HOME": str(cache / "torch"),
    # Xet left both model weight downloads at zero bytes for several minutes;
    # use Hugging Face's documented HTTPS transport instead.
    "HF_HUB_DISABLE_XET": "1",
    "HINDSIGHT_API_DATABASE_URL": "pg0://kubecon-experiment:55434",
    "HINDSIGHT_API_HOST": "127.0.0.1", "HINDSIGHT_API_PORT": "8890",
    "HINDSIGHT_API_LLM_PROVIDER": os.environ.get("EXPERIMENT_PROVIDER", "openai-responses"),
})
for key in keys:
    env["HINDSIGHT_API_" + key] = values[key]
if os.environ.get("EXPERIMENT_TEMPERATURE_NONE") == "1":
    env["HINDSIGHT_API_LLM_TEMPERATURE"] = "none"
process = subprocess.Popen([str(ROOT / ".venv" / "bin" / "hindsight-api")], env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
def terminate(_signum, _frame):
    process.terminate()
signal.signal(signal.SIGTERM, terminate)
signal.signal(signal.SIGINT, terminate)
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
with (cache / f"server-{stamp}.log").open("w") as log:
    for line in process.stdout:
        for secret in (values["LLM_API_KEY"], values["LLM_BASE_URL"]):
            line = line.replace(secret, "[REDACTED]")
        log.write(line)
        log.flush()
sys.exit(process.wait())
