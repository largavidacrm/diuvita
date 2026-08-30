#!/usr/bin/env python3
"""Enrich open candidate reviews by looking for official team/about pages."""
from __future__ import annotations

import argparse
import json
import sys
from html.parser import HTMLParser
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse

from capture_source_snapshot import FetchResult, decode_body, fetch_url, normalize_space
from enrich_candidate_review_from_url import patched_payload, update_review
from extract_clinic_profile_shadow import extract_from_fetch
from submit_discovery_candidates import load_env_file, run_psql, sql_literal


TEAM_LINK_TERMS = {
    "equipo": 10,
    "equipo-medico": 14,
    "equipo-médico": 14,
    "nuestro-equipo": 10,
    "quienes-somos": 9,
    "quienessomos": 9,
    "quienes": 7,
    "profesionales": 7,
    "especialistas": 7,
    "medicos": 6,
    "medicos-y-especialistas": 7,
    "médicos": 6,
    "doctors": 6,
    "team": 8,
    "our-team": 8,
    "about": 5,
    "about-us": 5,
    "nosotros": 5,
    "medical-team": 8,
}

AVOID_LINK_TERMS = (
    "aviso-legal",
    "blog",
    "cookies",
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "politica",
    "privacy",
    "privacidad",
    "terms",
    "youtube.com",
)


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href") or ""
        clean = normalize_space(href)
        if clean:
            self.links.append(clean)


def compact_host(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def is_same_site(base_url: str, candidate_url: str) -> bool:
    return compact_host(base_url) == compact_host(candidate_url)


def clean_candidate_url(base_url: str, href: str) -> str:
    href = normalize_space(href)
    lower = href.lower()
    if not href or lower.startswith(("mailto:", "tel:", "javascript:", "#")):
        return ""
    absolute = urljoin(base_url, href)
    parsed = urlparse(absolute)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    cleaned = parsed._replace(fragment="").geturl()
    if not is_same_site(base_url, cleaned):
        return ""
    if any(term in cleaned.lower() for term in AVOID_LINK_TERMS):
        return ""
    return cleaned


def team_url_score(url: str) -> int:
    parsed = urlparse(url)
    clean = (parsed.path + " " + parsed.query).lower().replace("_", "-")
    score = 0
    for term, weight in TEAM_LINK_TERMS.items():
        if term in clean:
            score += weight
    return score


def discover_team_urls(fetch: FetchResult, limit: int) -> list[str]:
    html = decode_body(fetch.body, fetch.content_type)
    parser = LinkParser()
    parser.feed(html)
    scored = []
    seen = set()
    for href in parser.links:
        url = clean_candidate_url(fetch.final_url or fetch.source_url, href)
        if not url or url in seen:
            continue
        seen.add(url)
        score = team_url_score(url)
        if score:
            scored.append((score, url))
    return [url for _, url in sorted(scored, key=lambda item: (-item[0], item[1]))[:limit]]


def as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if normalize_space(str(item or ""))]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def candidate_source_urls(payload: dict[str, Any]) -> list[str]:
    candidate = payload.get("candidate") or {}
    urls = []
    urls.extend(as_list(candidate.get("source_url")))
    urls.extend(as_list(payload.get("candidate_source_url")))
    urls.extend(as_list(candidate.get("website")))
    urls.extend(as_list(payload.get("candidate_website")))
    urls.extend(as_list(candidate.get("source_urls")))
    urls.extend(as_list(payload.get("source_urls")))
    seen = set()
    clean = []
    for url in urls:
        if not url or url in seen:
            continue
        seen.add(url)
        clean.append(url)
    return clean


def candidate_has_professionals(payload: dict[str, Any]) -> bool:
    candidate = payload.get("candidate") or {}
    return bool(as_list(candidate.get("profesionales")) or as_list(candidate.get("professionals")))


def load_open_candidate_reviews(limit: int, local_env: dict[str, str]) -> list[dict[str, Any]]:
    sql = f"""
select coalesce(jsonb_agg(to_jsonb(items) order by items.created_at asc), '[]'::jsonb)
from (
  select
    id,
    title,
    payload,
    created_at
  from public.review_queue
  where status = 'open'
    and review_type = 'candidate_clinic'
  order by created_at asc
  limit {int(limit)}
) items;
"""
    return json.loads(run_psql(sql, local_env) or "[]")


def extraction_professionals(extraction: dict[str, Any]) -> list[str]:
    profile = extraction.get("candidate_profile") or {}
    return as_list(profile.get("professionals"))


def try_extract_from_url(source_url: str, timeout: int) -> tuple[dict[str, Any] | None, str | None]:
    try:
        extraction = extract_from_fetch(fetch_url(source_url, timeout=timeout))
        return extraction, None
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as error:
        return None, str(error)


def enrich_review(row: dict[str, Any], args: argparse.Namespace, local_env: dict[str, str]) -> dict[str, Any]:
    payload = row.get("payload") or {}
    candidate = payload.get("candidate") or {}
    name = candidate.get("name") or payload.get("candidate_name") or row.get("title")

    if candidate_has_professionals(payload) and not args.include_with_professionals:
        return {"review_id": row.get("id"), "candidate_name": name, "status": "skipped_has_professionals"}

    seed_urls = candidate_source_urls(payload)[: args.max_seed_urls]
    if not seed_urls:
        return {"review_id": row.get("id"), "candidate_name": name, "status": "no_source_url"}

    tried: list[str] = []
    errors: list[dict[str, str]] = []
    discovered: list[str] = []

    for source_url in seed_urls:
        tried.append(source_url)
        extraction, error = try_extract_from_url(source_url, args.timeout)
        if error:
            errors.append({"source_url": source_url, "error": error})
        elif extraction and extraction_professionals(extraction):
            return finish_review(row, payload, extraction, source_url, args, local_env, tried, discovered, errors)

        try:
            fetch = fetch_url(source_url, timeout=args.timeout)
            for team_url in discover_team_urls(fetch, args.max_team_links):
                if team_url not in discovered and team_url not in seed_urls:
                    discovered.append(team_url)
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as link_error:
            errors.append({"source_url": source_url, "error": str(link_error)})

    for team_url in discovered:
        tried.append(team_url)
        extraction, error = try_extract_from_url(team_url, args.timeout)
        if error:
            errors.append({"source_url": team_url, "error": error})
            continue
        if extraction and extraction_professionals(extraction):
            return finish_review(row, payload, extraction, team_url, args, local_env, tried, discovered, errors)

    return {
        "review_id": row.get("id"),
        "candidate_name": name,
        "status": "not_found",
        "tried": tried,
        "discovered": discovered,
        "errors": errors,
    }


def finish_review(
    row: dict[str, Any],
    payload: dict[str, Any],
    extraction: dict[str, Any],
    source_url: str,
    args: argparse.Namespace,
    local_env: dict[str, str],
    tried: list[str],
    discovered: list[str],
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    patched, summary = patched_payload(payload, extraction, source_url)
    result = {
        "review_id": row.get("id"),
        "candidate_name": (patched.get("candidate") or {}).get("name") or row.get("title"),
        "status": "would_update",
        "source_url": source_url,
        "professionals": summary.get("professionals") or [],
        "tried": tried,
        "discovered": discovered,
        "errors": errors,
    }
    if not args.apply:
        return result
    updated = update_review(str(row.get("id")), patched, extraction, source_url, local_env)
    result["status"] = "updated"
    result["updated"] = updated
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--max-seed-urls", type=int, default=3)
    parser.add_argument("--max-team-links", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--include-with-professionals", action="store_true")
    parser.add_argument("--apply", action="store_true", help="Update candidate review cards in Supabase.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1.")

    local_env = load_env_file()
    rows = load_open_candidate_reviews(args.limit, local_env)
    results = [enrich_review(row, args, local_env) for row in rows]
    print(json.dumps({
        "mode": "apply" if args.apply else "dry_run",
        "reviews_seen": len(rows),
        "updated": sum(1 for item in results if item.get("status") == "updated"),
        "would_update": sum(1 for item in results if item.get("status") == "would_update"),
        "not_found": sum(1 for item in results if item.get("status") == "not_found"),
        "skipped": sum(1 for item in results if str(item.get("status") or "").startswith("skipped")),
        "items": results,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
