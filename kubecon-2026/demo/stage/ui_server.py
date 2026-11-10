"""Start a local UI with a clean environment and redacted console output."""

import sys

from config import ROOT, isolated_environment, load_config
from server import require_free_port, run_redacted


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("app", "control"):
        sys.exit("Usage: just app | just control")
    try:
        config = load_config()
    except ValueError as exc:
        sys.exit(str(exc))
    env = isolated_environment(config)
    if sys.argv[1] == "app":
        port = int(config["APP_PORT"])
        command = [str(ROOT / ".venv/bin/chainlit"), "run", "app.py", "--host", "127.0.0.1",
                   "--port", str(port), "--headless"]
        name = "Chainlit"
    else:
        port = int(config["HINDSIGHT_CP_PORT"])
        node = ROOT / ".local/bin/node"
        script = ROOT / ".local/control-plane/node_modules/@vectorize-io/hindsight-control-plane/bin/cli.js"
        if not node.is_file() or not script.is_file():
            sys.exit("Stage-local Node or Hindsight control plane is not installed")
        command = [str(node), str(script), "--hostname", "127.0.0.1", "--port", str(port),
                   "--api-url", f"http://127.0.0.1:{config['HINDSIGHT_PORT']}"]
        env.pop("LLM_API_KEY", None)  # The control plane does not need the Azure key.
        name = "Hindsight control plane"
    require_free_port(port, name)
    run_redacted(command, env, config["LLM_API_KEY"])


if __name__ == "__main__":
    main()
