"""Run another stage-local Python script with only the local .env environment."""

import os
import sys
from pathlib import Path

from config import ROOT, isolated_environment, load_config


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: isolated.py <stage-local-script> [arguments]")
    script = (ROOT / sys.argv[1]).resolve()
    if not script.is_relative_to(ROOT) or not script.is_file():
        sys.exit("Script must be a file inside demo/stage")
    try:
        env = isolated_environment(load_config())
    except ValueError as exc:
        sys.exit(str(exc))
    python = ROOT / ".venv/bin/python"
    os.chdir(ROOT)
    os.execve(str(python), [str(python), "-Es", str(script), *sys.argv[2:]], env)


if __name__ == "__main__":
    main()
