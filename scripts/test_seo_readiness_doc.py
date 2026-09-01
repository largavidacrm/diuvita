#!/usr/bin/env python3
"""Checks the internal SEO readiness gate stays aligned with Vitalarga limits."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "SEO_READINESS.md"
BUILD = ROOT / "build.py"
ADMIN = ROOT / "admin" / "index.html"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def has_all(text: str, fragments: list[str]) -> bool:
    lower = text.lower()
    return all(fragment.lower() in lower for fragment in fragments)


def main() -> None:
    doc = DOC.read_text(encoding="utf-8")
    build = BUILD.read_text(encoding="utf-8")
    admin = ADMIN.read_text(encoding="utf-8")

    check("https://www.vitalarga.com" in doc, "canonical domain missing")
    check("Diuvita" not in doc, "old brand should not appear in SEO readiness")
    check(has_all(doc, ["SEO tecnico", "SEO programatico", "esperar"]), "technical/programmatic SEO gate missing")
    check(has_all(doc, ["no es ranking", "recomendacion medica"]), "no-ranking/no-recommendation boundary missing")
    check(has_all(doc, ["Google Maps", "perfil real de la clinica"]), "Google Maps direct-profile rule missing")
    check(has_all(doc, ["bandeja de revision", "25"]), "review backlog gate missing")
    check(has_all(doc, ["propuesta revisable", "fuente"]), "agent proposal/source boundary missing")
    check(
        has_all(
            doc,
            [
                "REGCESS",
                "registro sanitario",
                "ultima verificacion",
                "fuente visible",
                "modalidad presencial, online o mixta",
                "idiomas",
                "pruebas concretas",
                "precio publico",
                "chequeo inicial",
                "duracion",
            ],
        ),
        "base comparable fields missing",
    )
    check(has_all(doc, ["sitemap.xml", "robots.txt", "canonical", "schema", "metadescriptions"]), "technical artifact inventory missing")
    check(has_all(doc, ["no hacen push", "no despliegan", "no escriben en Supabase"]), "read-only verification boundary missing")

    check('BASE = "https://www.vitalarga.com"' in build, "build canonical base missing")
    check('<link rel="canonical"' in build, "build canonical tag missing")
    check("sitemap.xml" in build and "robots.txt" in build, "build sitemap/robots generation missing")
    check('"@type": "WebSite"' in build, "WebSite schema missing")
    check('"@type": "MedicalClinic"' in build, "MedicalClinic schema missing")
    check('"@type": "Article"' in build, "Article schema missing")
    check('name="robots" content="noindex,nofollow"' in admin, "admin noindex marker missing")

    print("OK SEO readiness: technical gate and safety boundaries are documented")


if __name__ == "__main__":
    main()
