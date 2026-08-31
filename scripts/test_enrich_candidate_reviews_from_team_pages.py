#!/usr/bin/env python3
"""Checks candidate batch enrichment helpers."""
from argparse import Namespace

from capture_source_snapshot import FetchResult
from enrich_candidate_reviews_from_team_pages import (
    candidate_has_professionals,
    candidate_professionals,
    candidate_source_urls,
    clean_candidate_url,
    discover_team_urls,
    enrich_review,
    load_open_candidate_reviews,
    team_url_score,
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    payload = {
        "candidate_source_url": "https://clinic.example/longevity",
        "candidate": {
            "website": "https://clinic.example/",
            "source_urls": ["https://clinic.example/longevity", "https://clinic.example/quienes-somos"],
        },
    }
    check(
        candidate_source_urls(payload) == [
            "https://clinic.example/longevity",
            "https://clinic.example/",
            "https://clinic.example/quienes-somos",
        ],
        "candidate URLs should dedupe in useful order",
    )
    check(not candidate_has_professionals(payload), "empty candidate should not have professionals")
    payload["candidate"]["profesionales"] = ["Dra. Example"]
    check(candidate_has_professionals(payload), "candidate professionals should be detected")
    check(candidate_professionals(payload) == ["Dra. Example"], "candidate professionals should be listed")

    check(
        clean_candidate_url("https://clinic.example/a", "/quienes-somos#team") == "https://clinic.example/quienes-somos",
        "relative same-site team URL should be cleaned",
    )
    check(clean_candidate_url("https://clinic.example/a", "mailto:test@example.com") == "", "email links should be ignored")
    check(clean_candidate_url("https://clinic.example/a", "https://other.example/equipo") == "", "external links should be ignored")
    check(team_url_score("https://clinic.example/quienes-somos") > team_url_score("https://clinic.example/about"), "Spanish team pages should score higher")

    html = b"""
<!doctype html>
<html>
<body>
  <a href="/blog/equipo-maquinas">Blog</a>
  <a href="/contacto">Contacto</a>
  <a href="/quienes-somos">Quienes somos</a>
  <a href="/equipo-medico">Equipo medico</a>
  <a href="https://instagram.com/clinic">Instagram</a>
</body>
</html>
"""
    urls = discover_team_urls(
        FetchResult(
            source_url="https://clinic.example/",
            final_url="https://clinic.example/",
            status_code=200,
            content_type="text/html; charset=utf-8",
            body=html,
        ),
        limit=3,
    )
    check(urls[0] == "https://clinic.example/equipo-medico", "highest-scoring team URL should win")
    check("https://clinic.example/quienes-somos" in urls, "about/team URL should be included")
    check("https://clinic.example/equipo/" in urls, "common team archive URL should be included")
    check(all("instagram" not in url for url in urls), "social URLs should be ignored")

    fallback_urls = discover_team_urls(
        FetchResult(
            source_url="https://imda.example/",
            final_url="https://imda.example/",
            status_code=200,
            content_type="text/html; charset=utf-8",
            body=b"<html><body><a href='/quienes-somos'>Quienes somos</a></body></html>",
        ),
        limit=3,
    )
    check("https://imda.example/equipo/" in fallback_urls, "common team path should be tried when only about page is linked")

    skipped = enrich_review(
        {"id": "review-1", "title": "Regenera", "payload": payload},
        Namespace(
            timeout=15,
            max_seed_urls=3,
            max_team_links=5,
            include_with_professionals=False,
            apply=False,
        ),
        {},
    )
    check(skipped["status"] == "skipped_has_professionals", "existing candidate professionals should skip")
    check(skipped["professionals_count"] == 1, "skip should report professional count")
    check(skipped["professionals"] == ["Dra. Example"], "skip should report professional names")

    captured = {}

    def fake_run_psql(sql, local_env):
        captured["sql"] = sql
        return "[]"

    original_run_psql = load_open_candidate_reviews.__globals__["run_psql"]
    try:
        load_open_candidate_reviews.__globals__["run_psql"] = fake_run_psql
        load_open_candidate_reviews(8, {}, candidate_query="Regenera")
    finally:
        load_open_candidate_reviews.__globals__["run_psql"] = original_run_psql
    check("like '%regenera%'" in captured["sql"], "candidate query filter should be applied")
    print("OK candidate batch enrichment: team page discovery")


if __name__ == "__main__":
    main()
