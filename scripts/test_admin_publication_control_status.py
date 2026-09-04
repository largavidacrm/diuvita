#!/usr/bin/env python3
"""Checks that the admin surfaces manual publication status."""
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
        "function publicationHasPendingChanges",
        "function renderPublicationBanner",
        "function requestPublicSiteRebuildNow",
        "admin_request_public_site_rebuild_now",
        "admin_publication_control_summary",
        "rebuild_hook_configured",
        "publication_mode",
        "automatic_rebuild_enabled",
        "rebuild_batch_minutes",
        "last_public_site_rebuild_requested_at",
        "last_public_site_change_at",
        "pending_public_site_rebuild",
        "can_request_public_site_rebuild_now",
        "Publicación web",
        "Publicación web",
        "Último rebuild",
        "Actualizar web ahora",
        "Hay cambios guardados que todavía no se ven online.",
        "Netlify puede tardar unos minutos.",
        "Agrupada · ",
        "Manual · pendiente",
        "Cambios pendientes",
        "No se pudo leer Supabase.",
        "var publicationControl = await loadPublicationControl();",
    ]:
        check(marker in index, f"missing publication-control marker: {marker}")

    css = (ROOT / "admin" / "admin.css").read_text(encoding="utf-8")
    for marker in [
        ".publication-banner",
        ".publication-banner.is-pending",
        ".publication-banner .btn",
    ]:
        check(marker in css, f"missing publication banner style: {marker}")

    print("OK admin publication control: manual publication status visible")


if __name__ == "__main__":
    main()
