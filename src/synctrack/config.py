"""Minimal .env loader (no extra pip dependency).

Reads KEY=VALUE lines from a local .env file (gitignored -- never commit
real credentials) into os.environ, without overriding anything already set
in the real environment.
"""

import os
from pathlib import Path

_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"


def load_env():
    if not _ENV_PATH.exists():
        return
    for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_env()
