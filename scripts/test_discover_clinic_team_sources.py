#!/usr/bin/env python3
"""Checks for discovering official clinic team/about source pages."""

from discover_clinic_team_sources import (
    TEAM_SOURCE_TYPE,
    clean_candidate_url,
    discover_common_team_links,
    discover_team_links,
    discovery_row,
    insert_sources_sql,
    merge_team_candidates,
    source_metadata,
)
from capture_source_snapshot import FetchResult


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    html = """
<!doctype html>
<html>
<body>
  <a href="/tratamientos/longevidad/">Longevidad</a>
  <a href="/quienes-somos">Quiénes somos</a>
  <a href="/equipo-arvila-magna-medicina-integrativa/">Equipo Arvila Magna</a>
  <a href="/profesionales">Profesionales médicos</a>
  <a href="https://otra-clinica.example/equipo">Equipo externo</a>
  <a href="/blog/equipo-2025">Blog equipo</a>
</body>
</html>
"""
    links = discover_team_links("https://arvilamagna.example/", html, max_links=5)
    urls = [item.url for item in links]
    check(
        "https://arvilamagna.example/equipo-arvila-magna-medicina-integrativa/" in urls,
        "Arvila-style team page should be discovered",
    )
    check(
        "https://arvilamagna.example/quienes-somos/" in urls,
        "Regenera-style about page should be discovered",
    )
    check(
        "https://arvilamagna.example/profesionales/" in urls,
        "professionals page should be discovered",
    )
    check(
        all("otra-clinica" not in item.url and "/blog/" not in item.url for item in links),
        "external or blog links should not be proposed",
    )
    check(
        clean_candidate_url("https://clinic.example/base/", "/equipo#doctor") == "https://clinic.example/equipo/",
        "candidate URL should be canonicalized",
    )
    check(
        clean_candidate_url("https://clinic.example/base/", "/equipo.html#doctor") == "https://clinic.example/equipo.html",
        "file-like team URLs should not receive a trailing slash",
    )
    calls = []

    def fake_fetch(url, timeout=15):
        calls.append(url)
        if url.endswith("/equipo/"):
            body = b"<html><title>Miembros</title><body>Miembros del equipo Dra. Example Name</body></html>"
            return FetchResult(url, url, 200, "text/html; charset=utf-8", body)
        raise OSError("not found")

    common_links = discover_common_team_links("https://imda.example/", 15, 2, fake_fetch)
    check(calls[:2] == ["https://imda.example/equipo/", "https://imda.example/equipo-medico/"], "common team paths should be probed narrowly")
    check(common_links and common_links[0].url == "https://imda.example/equipo/", "existing common team page should be discovered")
    combined = merge_team_candidates([*links, *common_links], max_links=3)
    check("https://imda.example/equipo/" in [item.url for item in combined], "common team page should survive merge")

    clinic = {
        "clinic_id": "00000000-0000-0000-0000-000000000001",
        "slug": "arvila-magna",
        "display_name": "Clínica Arvila Magna",
        "city": "Barcelona",
        "status": "published",
        "website": "https://arvilamagna.example/",
    }
    row = discovery_row(clinic, links[0], already_stored=False)
    metadata = source_metadata(clinic, links[0])
    sql = insert_sources_sql([row])

    check(row["source_type"] == TEAM_SOURCE_TYPE, "source type should identify team pages")
    check(metadata["profile_fields_changed"] is False, "metadata should mark no profile edits")
    check(metadata["requires_human_review"] is False, "metadata should not add review pressure")
    check("official_team_page" in sql, "SQL should store team source type")
    check("profile_fields_changed" in sql, "SQL should preserve no-profile-edit metadata")
    check("not exists" in sql.lower(), "SQL should avoid duplicate source records")
    print("OK team source discovery: team/about pages can become safe internal sources")


if __name__ == "__main__":
    main()
