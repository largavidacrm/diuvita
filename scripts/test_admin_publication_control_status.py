#!/usr/bin/env python3
"""Checks that the admin surfaces publication batching status."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    index = (ROOT / "admin" / "index.html").read_text(encoding="utf-8")

    for marker in [
        "function emptyPublicationControl",
        "function loadPublicationControl",
        "function publicationControlLabel",
        "function publicationControlDetail",
        "admin_publication_control_summary",
        "rebuild_hook_configured",
        "rebuild_batch_minutes",
        "last_public_site_rebuild_requested_at",
        "Publicación agrupada",
        "Publicación web",
        "Último rebuild",
        "Agrupada · ",
        "No se pudo leer Supabase.",
        "var publicationControl = await loadPublicationControl();",
    ]:
        check(marker in index, f"missing publication-control marker: {marker}")

    print("OK admin publication control: batching status visible")


if __name__ == "__main__":
    main()
