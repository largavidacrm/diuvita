#!/usr/bin/env python3
"""Checks for discovering official clinic contact/location source pages."""

from discover_clinic_location_sources import (
    LOCATION_SOURCE_TYPE,
    clean_candidate_url,
    discover_location_links,
    discovery_row,
    insert_sources_sql,
    source_metadata,
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    html = """
<!doctype html>
<html>
<body>
  <a href="/tratamientos/longevidad/">Longevidad</a>
  <a href="/contacto/">Contacto</a>
  <a href="/donde-estamos">Dónde estamos</a>
  <a href="/sedes/madrid/">Sedes Madrid</a>
  <a href="/clinicas/">Clínicas</a>
  <a href="/centros-clinicos/madrid/">Centros clínicos Madrid</a>
  <a href="https://otra-clinica.example/contacto">Contacto externo</a>
  <a href="/blog/sedes-longevidad">Blog sedes</a>
  <a href="/equipo/">Equipo médico</a>
  <a href="/primera-visita/">Primera visita</a>
  <a href="/mapa-web/">Mapa Web</a>
  <a href="/clinicas-analisis-clinicos-en-madrid/">Análisis</a>
</body>
</html>
"""
    links = discover_location_links("https://clinic.example/", html, max_links=5)
    urls = [item.url for item in links]
    check("https://clinic.example/contacto/" in urls, "contact page should be discovered")
    check("https://clinic.example/donde-estamos/" in urls, "where-we-are page should be discovered")
    check("https://clinic.example/sedes/madrid/" in urls, "location branch should be discovered")
    check("https://clinic.example/centros-clinicos/madrid/" in urls, "clinical center pages should be discovered")
    check(
        all(
            "otra-clinica" not in item.url
            and "/blog/" not in item.url
            and "/equipo/" not in item.url
            and "/clinicas/" not in item.url
            and "/primera-visita/" not in item.url
            and "/mapa-web/" not in item.url
            and "/clinicas-analisis-clinicos-en-madrid/" not in item.url
            for item in links
        ),
        "external, blog, team or broad non-location links should not be proposed",
    )
    check(
        clean_candidate_url("https://clinic.example/base/", "/contacto#mapa") == "https://clinic.example/contacto/",
        "candidate URL should be canonicalized",
    )

    clinic = {
        "clinic_id": "00000000-0000-0000-0000-000000000001",
        "slug": "example-clinic",
        "display_name": "Example Clinic",
        "city": "Madrid",
        "status": "published",
        "website": "https://clinic.example/",
    }
    row = discovery_row(clinic, links[0], already_stored=False)
    metadata = source_metadata(clinic, links[0])
    sql = insert_sources_sql([row])

    check(row["source_type"] == LOCATION_SOURCE_TYPE, "source type should identify location pages")
    check(metadata["profile_fields_changed"] is False, "metadata should mark no profile edits")
    check(metadata["requires_human_review"] is False, "metadata should not add review pressure")
    check("official_location_page" in sql, "SQL should store location source type")
    check("página de sedes/contacto" in sql, "SQL should preserve readable source title")
    check("profile_fields_changed" in sql, "SQL should preserve no-profile-edit metadata")
    check("not exists" in sql.lower(), "SQL should avoid duplicate source records")
    print("OK location source discovery: contact/location pages can become safe internal sources")


if __name__ == "__main__":
    main()
