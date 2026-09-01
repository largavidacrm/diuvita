#!/usr/bin/env python3
"""Checks for the safe local dashboard server helper."""
from pathlib import Path
from tempfile import TemporaryDirectory
import errno

from serve_local_dashboard import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    bind_error_message,
    dashboard_root,
    ensure_dist_ready,
    ensure_loopback_host,
    local_version_label,
    make_handler,
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def exits(func, *args):
    try:
        func(*args)
    except SystemExit:
        return True
    return False


def main():
    root = Path("/tmp/example-worktree")
    dist = root / "dist"
    handler = make_handler(dist)

    check(DEFAULT_HOST == "127.0.0.1", "server should default to loopback")
    check(DEFAULT_PORT == 8765, "dashboard port should stay familiar")
    check(dashboard_root(root) == dist, "server should use dist/ only")
    check(handler.keywords["directory"] == str(dist), "handler should serve the generated dist directory")
    check(str(root) != handler.keywords["directory"], "handler must not serve the worktree root")
    busy_message = bind_error_message(DEFAULT_HOST, DEFAULT_PORT, OSError(errno.EADDRINUSE, "busy"))
    permission_message = bind_error_message(DEFAULT_HOST, DEFAULT_PORT, OSError(errno.EPERM, "blocked"))
    check("Prueba primero http://127.0.0.1:8765/admin/" in busy_message, "busy port message should point Daniel to the dashboard URL")
    check("--port 8766" in busy_message, "busy port message should suggest the next port")
    check("permiso local" in permission_message, "permission message should be user-friendly")
    check(local_version_label(root) == "no disponible", "missing git metadata should stay user-friendly")
    check(exits(ensure_loopback_host, "0.0.0.0"), "network-exposed hosts should be blocked")
    ensure_loopback_host("localhost")

    with TemporaryDirectory() as tmp:
        tmp_dist = Path(tmp) / "dist"
        check(exits(ensure_dist_ready, tmp_dist), "missing dist/admin/index.html should be explicit")
        (tmp_dist / "admin").mkdir(parents=True)
        (tmp_dist / "admin" / "index.html").write_text("<!doctype html>", encoding="utf-8")
        ensure_dist_ready(tmp_dist)

    print("OK local dashboard server: serves dist only")


if __name__ == "__main__":
    main()
