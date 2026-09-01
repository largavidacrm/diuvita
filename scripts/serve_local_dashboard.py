#!/usr/bin/env python3
"""Serve the generated Vitalarga site locally without exposing the worktree."""
from __future__ import annotations

import argparse
import errno
import functools
import http.server
import socketserver
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def dashboard_root(root: Path = ROOT) -> Path:
    return root / "dist"


def ensure_dist_ready(dist: Path = DIST) -> None:
    if not (dist / "admin" / "index.html").is_file():
        raise SystemExit("Falta dist/admin/index.html. Ejecuta primero: python3 build.py")


def ensure_loopback_host(host: str) -> None:
    if host not in LOOPBACK_HOSTS:
        raise SystemExit("Servidor local bloqueado: usa 127.0.0.1, localhost o ::1.")


def make_handler(dist: Path = DIST) -> Any:
    return functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(dist))


def local_version_label(root: Path = ROOT) -> str:
    try:
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        ).stdout.strip()
        commit = subprocess.run(
            ["git", "log", "-1", "--oneline"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "no disponible"
    if branch and commit:
        return f"{branch} · {commit}"
    return commit or branch or "no disponible"


def bind_error_message(host: str, port: int, error: OSError) -> str:
    url = f"http://{host}:{port}/admin/"
    if error.errno == errno.EADDRINUSE:
        return (
            f"El panel local ya tiene algo usando el puerto {port}. "
            f"Prueba primero {url}. Si no carga, usa otro puerto, por ejemplo --port {port + 1}."
        )
    if error.errno in {errno.EACCES, errno.EPERM}:
        return (
            f"No se pudo abrir {url} por permisos locales. "
            "Codex puede intentarlo de nuevo con permiso local; no afecta a producción."
        )
    return f"No se pudo abrir {url}: {error}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve dist/ locally for Vitalarga review.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ensure_loopback_host(args.host)
    if args.port < 1024 or args.port > 65535:
        raise SystemExit("--port debe estar entre 1024 y 65535.")
    dist = dashboard_root()
    ensure_dist_ready(dist)
    handler = make_handler(dist)
    try:
        with ReusableTCPServer((args.host, args.port), handler) as httpd:
            print(f"Dashboard local: http://{args.host}:{args.port}/admin/")
            print("Si tienes varias pestañas locales, usa esta URL.")
            print(f"Version local: {local_version_label()}")
            print(f"Sirviendo solo: {dist}")
            httpd.serve_forever()
    except OSError as error:
        raise SystemExit(bind_error_message(args.host, args.port, error))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
