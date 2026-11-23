#!/usr/bin/env python3
"""Fail if the prepared images or Ollama model manifests drift from the lock file."""

import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "assets.lock.json").read_text())
PROJECT = os.environ.get("LAB_PROJECT", "offline-doc-lab")


def run(*args):
    return subprocess.run(args, check=True, text=True, capture_output=True).stdout.strip()


def main():
    for name, reference in LOCK["images"].items():
        actual = json.loads(run("docker", "image", "inspect", reference))[0]
        if actual["Os"] + "/" + actual["Architecture"] != LOCK["platform"]:
            raise ValueError(f"{name}: wrong local platform")
        if reference.split("@", 1)[1] not in " ".join(actual["RepoDigests"]):
            raise ValueError(f"{name}: image digest does not match lock")
        print(f"PASS image {name}: {reference}")

    container = run(
        "docker", "compose", "-p", PROJECT, "-f", str(ROOT / "compose.yaml"),
        "ps", "-q", "ollama",
    )
    if not container:
        raise ValueError("Ollama container is not running")
    for name, expected in LOCK["models"].items():
        model, tag = name.split(":", 1)
        path = f"/root/.ollama/models/manifests/registry.ollama.ai/library/{model}/{tag}"
        observed = run("docker", "exec", container, "sha256sum", path).split()[0]
        if "sha256:" + observed != expected:
            raise ValueError(f"{name}: model manifest mismatch: sha256:{observed}")
        print(f"PASS model {name}: {expected}")


if __name__ == "__main__":
    try:
        main()
    except (subprocess.CalledProcessError, ValueError, KeyError) as exc:
        print(f"FAIL asset verification: {exc}", file=sys.stderr)
        raise SystemExit(1)
