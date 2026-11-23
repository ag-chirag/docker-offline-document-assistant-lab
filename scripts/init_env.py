#!/usr/bin/env python3
"""Create disposable local credentials without printing or committing them."""

from pathlib import Path
import os
import secrets
import sys


root = Path(__file__).resolve().parents[1]
target = root / ".env"
if target.exists():
    print(".env already exists; refusing to overwrite it", file=sys.stderr)
    raise SystemExit(1)
template = (root / ".env.example").read_text()
template = template.replace("replace-with-a-unique-random-password", secrets.token_urlsafe(24))
template = template.replace("replace-with-a-different-unique-random-secret", secrets.token_urlsafe(36))
descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(descriptor, "w") as stream:
    stream.write(template)
print("Created private .env for this disposable project")
