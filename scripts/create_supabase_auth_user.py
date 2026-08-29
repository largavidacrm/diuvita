#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create or verify a Supabase Auth user without storing the password."""
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


def api_call(url, key, path, payload):
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url.rstrip("/") + path,
        data=data,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8"))
        except Exception:
            body = {"message": str(exc)}
        return exc.code, body


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: scripts/create_supabase_auth_user.py email@example.com")

    email = sys.argv[1].strip().lower()
    if "@" not in email:
        raise SystemExit("Use a valid email address.")

    env = env_values()
    url = env.get("SUPABASE_URL")
    key = env.get("SUPABASE_PUBLISHABLE_KEY")
    if not url or not key:
        raise SystemExit("Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in .env first.")

    password = getpass.getpass("Password: ")
    if len(password) < 6:
        raise SystemExit("Password must be at least 6 characters.")

    status, body = api_call(url, key, "/auth/v1/signup", {"email": email, "password": password})
    if 200 <= status < 300:
        if body.get("session"):
            print("Auth user ready: login works now.")
        else:
            print("Auth user created: email confirmation may be required before login.")
        return

    message = str(body.get("msg") or body.get("message") or body)
    if "already" not in message.lower() and "registered" not in message.lower():
        raise SystemExit(f"Could not create user: {message}")

    status, body = api_call(
        url,
        key,
        "/auth/v1/token?grant_type=password",
        {"email": email, "password": password},
    )
    if 200 <= status < 300 and body.get("access_token"):
        print("Auth user already existed: login works with this password.")
        return

    message = str(body.get("msg") or body.get("message") or body)
    raise SystemExit(f"User already exists, but login did not work with this password: {message}")


if __name__ == "__main__":
    main()
