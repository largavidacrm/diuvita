#!/usr/bin/env python3
"""Decide whether Netlify can skip a production build.

Netlify expects exit code 0 to skip the build and exit code 1 to continue.
This script is deliberately conservative: unknown files trigger a build.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys


BUILD_FILES = {
    "build.py",
    "netlify.toml",
}

BUILD_PREFIXES = (
    "admin/",
    "assets/",
    "data/",
)

SAFE_SKIP_FILES = {
    ".env.example",
    "AGENTS.md",
    "README.md",
}

SAFE_SKIP_PREFIXES = (
    ".github/",
    "docs/",
    "pendientes/",
    "scripts/",
    "supabase/",
)


def normalize_path(path: str) -> str:
    clean = path.strip().replace("\\", "/")
    while clean.startswith("./"):
        clean = clean[2:]
    return clean


def path_requires_build(path: str) -> tuple[bool, str]:
    clean = normalize_path(path)
    if not clean:
        return False, "empty"
    if clean in BUILD_FILES:
        return True, f"{clean} changes build configuration"
    if any(clean.startswith(prefix) for prefix in BUILD_PREFIXES):
        return True, f"{clean} changes public/admin output"
    if clean in SAFE_SKIP_FILES:
        return False, f"{clean} is internal documentation/config guidance"
    if any(clean.startswith(prefix) for prefix in SAFE_SKIP_PREFIXES):
        return False, f"{clean} is internal operational work"
    return True, f"{clean} is not classified; building safely"


def should_skip_build(paths: list[str]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    normalized = [normalize_path(path) for path in paths if normalize_path(path)]
    if not normalized:
        return True, ["No changed files detected."]
    for path in normalized:
        requires_build, reason = path_requires_build(path)
        reasons.append(reason)
        if requires_build:
            return False, reasons
    return True, reasons


def changed_files_between(base: str, head: str) -> list[str] | None:
    result = subprocess.run(
        ["git", "diff", "--name-only", base, head],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        return None
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--files",
        nargs="*",
        help="Test mode: classify these paths instead of reading Netlify env vars.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.files is not None:
        paths = args.files
    else:
        base = os.environ.get("CACHED_COMMIT_REF", "").strip()
        head = os.environ.get("COMMIT_REF", "").strip()
        if not base or not head:
            print("Netlify commit refs missing; building safely.")
            return 1
        paths = changed_files_between(base, head)
        if paths is None:
            print("Could not inspect changed files; building safely.")
            return 1

    skip, reasons = should_skip_build(paths)
    decision = "Skipping Netlify build." if skip else "Running Netlify build."
    print(decision)
    for reason in reasons:
        print(f"- {reason}")
    return 0 if skip else 1


if __name__ == "__main__":
    sys.exit(main())
