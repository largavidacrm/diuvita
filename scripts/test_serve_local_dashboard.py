#!/usr/bin/env python3
"""Checks for the safe local dashboard server helper."""
from pathlib import Path
from tempfile import TemporaryDirectory

from serve_local_dashboard import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    dashboard_root,
    ensure_dist_ready,
    ensure_loopback_host,
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
