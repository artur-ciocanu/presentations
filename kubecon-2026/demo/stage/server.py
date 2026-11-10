"""Run the phase-one Hindsight server with only stage-local configuration."""

import re
import signal
import socket
import subprocess
import sys

from config import ROOT, isolated_environment, load_config
from model_cache import missing_models


def server_environment(config):
    environment = isolated_environment(config)
    environment.update({
        "HINDSIGHT_API_LLM_API_KEY": config["LLM_API_KEY"],
        "HINDSIGHT_API_LLM_BASE_URL": config["LLM_BASE_URL"],
        "HINDSIGHT_API_LLM_MODEL": config["LLM_MODEL"],
    })
    return environment


def redact(line, secret):
    line = line.replace(secret, "[REDACTED]")
    return re.sub(r"(://)[^/@\s:]+:[^/@\s]+@", r"\1[REDACTED]@", line)


def require_free_port(port, name):
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            sys.exit(f"{name} port {port} is already in use; stop the existing service first")


def run_redacted(command, environment, secret):
    process = subprocess.Popen(command, cwd=ROOT, env=environment,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, errors="replace", bufsize=1)

    def forward(signum, _frame):
        if process.poll() is None:
            process.send_signal(signum)

    signal.signal(signal.SIGINT, forward)
    signal.signal(signal.SIGTERM, forward)
    assert process.stdout is not None
    for line in process.stdout:
        sys.stdout.write(redact(line, secret))
        sys.stdout.flush()
    sys.exit(process.wait())


def main():
    try:
        config = load_config()
    except ValueError as exc:
        sys.exit(str(exc))
    missing = missing_models()
    if missing:
        sys.exit("Local model cache incomplete: " + ", ".join(missing) + ". Run just warm-models before the demo.")
    port = int(config["HINDSIGHT_PORT"])
    require_free_port(port, "Hindsight")
    command = [str(ROOT / ".venv/bin/hindsight-api"), "--host", "127.0.0.1",
               "--port", str(port), "--log-level", "warning"]
    run_redacted(command, server_environment(config), config["LLM_API_KEY"])


if __name__ == "__main__":
    main()
