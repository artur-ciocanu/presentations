"""Redact credentials before writing diagnostic output."""

import re
import sys

from config import load_config


def main():
    secret = load_config()["LLM_API_KEY"]
    for line in sys.stdin:
        line = line.replace(secret, "[REDACTED]")
        line = re.sub(r"(://)[^/@\s:]+:[^/@\s]+@", r"\1[REDACTED]@", line)
        sys.stdout.write(line)
        sys.stdout.flush()


if __name__ == "__main__":
    main()
