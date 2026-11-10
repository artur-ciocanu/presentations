"""Wait for the local API to become healthy, then run the phase-one probe."""

import os
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

from config import ROOT, isolated_environment, load_config


def main():
    try:
        cfg = load_config()
    except ValueError as exc:
        sys.exit(str(exc))
    health = f"http://127.0.0.1:{cfg['HINDSIGHT_PORT']}/health"
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        try:
            with urlopen(health, timeout=2) as response:
                if response.status == 200:
                    print("Hindsight health endpoint: OK", flush=True)
                    os.execve(str(ROOT / ".venv/bin/python"),
                              [str(ROOT / ".venv/bin/python"), str(ROOT / "phase1_probe.py")],
                              isolated_environment(cfg))
        except (URLError, TimeoutError, OSError):
            pass
        time.sleep(2)
    sys.exit("Hindsight did not become healthy within 300 seconds; see redacted .cache/server.log")


if __name__ == "__main__":
    main()
