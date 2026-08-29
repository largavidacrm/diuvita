#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check Supabase Auth login without storing the password."""
import getpass
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"


def env_values():
    values = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip("\"'")
    return values


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: scripts/check_supabase_auth_login.py email@example.com")

    email = sys.argv[1].strip().lower()
    env = env_values()
    url = env.get("SUPABASE_URL")
    key = env.get("SUPABASE_PUBLISHABLE_KEY")
    if not url or not key:
        raise SystemExit("Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in .env first.")

    password = getpass.getpass("Password: ")
    payload = json.dumps({"email": email, "password": password}).encode("utf-8")
    request = urllib.request.Request(
        url.rstrip("/") + "/auth/v1/token?grant_type=password",
        data=payload,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8"))
        except Exception:
            body = {"message": str(exc)}
        message = body.get("msg") or body.get("message") or "login failed"
        raise SystemExit(f"Login failed: {message}")

    if body.get("access_token"):
        print("Login works.")
        return
    raise SystemExit("Login failed: no access token returned.")


if __name__ == "__main__":
    main()
