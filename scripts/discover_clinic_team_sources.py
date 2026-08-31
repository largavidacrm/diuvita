#!/usr/bin/env python3
"""Discover official team/about pages for visible Vitalarga clinics.

The tool reads visible clinics, fetches their official homepage, and proposes
same-domain pages that look like team, doctors, professionals, or about pages.
Apply mode only stores source_records for later review; it never edits clinic
profiles, creates public pages, or resolves review_queue items.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urldefrag, urljoin, urlparse

from capture_source_snapshot import FetchResult, decode_body, fetch_url, normalize_space
from submit_discovery_candidates import load_env_file, run_psql, sql_literal


DISCOVERER_NAME = "vitalarga-team-source-discoverer"
DISCOVERER_VERSION = "2026-08-30"
TEAM_SOURCE_TYPE = "official_team_page"
MAX_LINKS_PER_CLINIC = 3

TEAM_TERMS = (
    ("equipo medico", 30),
    ("equipo medicos", 30),
    ("equipo", 24),
    ("profesionales", 24),
    ("medicos", 22),
    ("doctores", 22),
    ("especialistas", 20),
    ("quienes somos", 20),
    ("quienes-somos", 20),
    ("sobre nosotros", 16),
    ("nosotros", 10),
    ("team", 16),
    ("staff", 14),
    ("about", 10),
)
NOISE_TERMS = (
    "aviso legal",
    "blog",
    "carrito",
    "contacto",
    "cookies",
    "evento",
    "login",
    "noticia",
    "politica",
    "política",
    "privacidad",
    "shop",
    "tienda",
)
SKIPPED_EXTENSIONS = re.compile(r"\.(?:7z|avi|css|docx?|gif|jpe?g|js|mp4|pdf|png|rar|svg|webp|xlsx?|zip)$", re.I)


@dataclass(frozen=True)
class LinkCandidate:
    url: str
    label: str
    score: int
    reason: str


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if tag == "a" and not self._skip_depth:
            self._href = dict(attrs).get("href") or ""
            self._parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "a" and self._href is not None:
            self.links.append((self._href, normalize_space(" ".join(self._parts))))
            self._href = None
            self._parts = []
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._href is not None and not self._skip_depth:
            clean = normalize_space(data)
            if clean:
                self._parts.append(clean)


def fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return normalized.encode("ascii", "ignore").decode("ascii").lower()


def host_key(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def clean_candidate_url(base_url: str, href: str) -> str:
    raw = normalize_space(href)
    if not raw or raw.startswith(("#", "mailto:", "tel:", "javascript:")):
        return ""
    absolute = urljoin(base_url, raw)
    absolute, _fragment = urldefrag(absolute)
    parsed = urlparse(absolute)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    if host_key(absolute) != host_key(base_url):
        return ""
    if SKIPPED_EXTENSIONS.search(parsed.path):
        return ""
    canonical = parsed._replace(query="").geturl()
    if re.search(r"\.[a-z0-9]{2,6}$", parsed.path, flags=re.I):
        return canonical
    return canonical.rstrip("/") + "/"


def score_candidate(url: str, label: str) -> tuple[int, str]:
    parsed = urlparse(url)
    haystack = fold(" ".join([parsed.path.replace("/", " "), label]))
    if any(term in haystack for term in NOISE_TERMS):
        return 0, "noise"
    matches = [(term, points) for term, points in TEAM_TERMS if term in haystack]
    if not matches:
        return 0, "no-team-term"
    score = sum(points for _term, points in matches)
    depth = len([part for part in parsed.path.split("/") if part])
    if depth <= 2:
        score += 4
    if label and len(label) <= 60:
        score += 2
    reason = ", ".join(term for term, _points in matches[:3])
    return score, reason


def discover_team_links(base_url: str, html_text: str, max_links: int = MAX_LINKS_PER_CLINIC) -> list[LinkCandidate]:
    parser = LinkParser()
    parser.feed(html_text)
    by_url: dict[str, LinkCandidate] = {}
    for href, label in parser.links:
        url = clean_candidate_url(base_url, href)
        if not url:
            continue
        score, reason = score_candidate(url, label)
        if score <= 0:
            continue
        candidate = LinkCandidate(url=url, label=label, score=score, reason=reason)
        existing = by_url.get(url)
        if not existing or candidate.score > existing.score:
            by_url[url] = candidate
    return sorted(by_url.values(), key=lambda item: (-item.score, item.url))[:max_links]


def load_visible_clinics(limit: int, clinic_slug: str | None, local_env: dict[str, str]) -> list[dict[str, Any]]:
    clinic_filter = f"and c.slug = {sql_literal(clinic_slug)}" if clinic_slug else ""
    sql = f"""
select coalesce(jsonb_agg(to_jsonb(items) order by items.status_order, items.display_name), '[]'::jsonb)
from (
  select
    c.id as clinic_id,
    c.slug,
    c.display_name,
    c.city,
    c.country,
    c.status,
    c.website,
    case when c.status = 'published' then 0 else 1 end as status_order
  from public.clinics c
  where c.status in ('published', 'preliminary')
    and c.website ~* '^https?://'
    {clinic_filter}
  order by status_order, c.display_name
  limit {max(1, min(100, int(limit)))}
) items;
"""
    return json.loads(run_psql(sql, local_env) or "[]")


def load_existing_source_urls(clinic_id: str, local_env: dict[str, str]) -> set[str]:
    sql = f"""
select coalesce(jsonb_agg(sr.source_url order by sr.source_url), '[]'::jsonb)
from public.source_records sr
where sr.clinic_id = {sql_literal(clinic_id)}::uuid
  and sr.entity_type = 'clinic';
"""
    return set(json.loads(run_psql(sql, local_env) or "[]"))


def source_metadata(clinic: dict[str, Any], candidate: LinkCandidate) -> dict[str, Any]:
    return {
        "discovered_by": DISCOVERER_NAME,
        "discoverer_version": DISCOVERER_VERSION,
        "reason": "official_team_or_about_page_discovered_from_homepage",
        "discovered_from": clinic.get("website"),
        "link_label": candidate.label,
        "link_score": candidate.score,
        "link_reason": candidate.reason,
        "profile_fields_changed": False,
        "requires_human_review": False,
    }


def discovery_row(clinic: dict[str, Any], candidate: LinkCandidate, already_stored: bool) -> dict[str, Any]:
    return {
        "clinic_id": clinic.get("clinic_id"),
        "clinic_slug": clinic.get("slug"),
        "clinic_name": clinic.get("display_name"),
        "city": clinic.get("city"),
        "status": clinic.get("status"),
        **asdict(candidate),
        "already_stored": already_stored,
        "source_type": TEAM_SOURCE_TYPE,
        "metadata": source_metadata(clinic, candidate),
    }


def discover_for_clinic(
    clinic: dict[str, Any],
    timeout: int,
    max_links_per_clinic: int,
    local_env: dict[str, str],
    fetcher: Callable[..., FetchResult] = fetch_url,
) -> dict[str, Any]:
    website = str(clinic.get("website") or "")
    base = website.rstrip("/") + "/"
    try:
        result = fetcher(base, timeout=timeout)
        html_text = decode_body(result.body, result.content_type)
        links = discover_team_links(result.final_url or base, html_text, max_links=max_links_per_clinic)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as error:
        return {
            "clinic_slug": clinic.get("slug"),
            "clinic_name": clinic.get("display_name"),
            "website": website,
            "status": "failed",
            "error": str(error),
            "items": [],
        }

    existing = load_existing_source_urls(str(clinic.get("clinic_id") or ""), local_env)
    items = [discovery_row(clinic, candidate, candidate.url in existing) for candidate in links]
    return {
        "clinic_slug": clinic.get("slug"),
        "clinic_name": clinic.get("display_name"),
        "website": website,
        "status": "ready",
        "items": items,
    }


def insert_sources_sql(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "select jsonb_build_object('inserted', '[]'::jsonb, 'inserted_count', 0, 'generated_at', now());"
    values = []
    for row in rows:
        title = f"{row.get('clinic_name') or row.get('clinic_slug')} · página de equipo"
        metadata = json.dumps(row.get("metadata") or {}, ensure_ascii=False)
        values.append(
            "("
            + ", ".join(
                [
                    sql_literal(row.get("clinic_id")) + "::uuid",
                    sql_literal(row.get("url")),
                    sql_literal(title),
                    sql_literal(metadata) + "::jsonb",
                ]
            )
            + ")"
        )
    return f"""
with incoming(clinic_id, source_url, source_title, metadata) as (
  values
    {",\n    ".join(values)}
),
inserted as (
  insert into public.source_records (
    clinic_id,
    entity_type,
    entity_id,
    source_url,
    source_title,
    source_type,
    retrieved_at,
    metadata
  )
  select
    incoming.clinic_id,
    'clinic',
    incoming.clinic_id,
    incoming.source_url,
    incoming.source_title,
    {sql_literal(TEAM_SOURCE_TYPE)},
    now(),
    incoming.metadata
  from incoming
  where not exists (
    select 1
    from public.source_records sr
    where sr.clinic_id = incoming.clinic_id
      and sr.entity_type = 'clinic'
      and sr.source_url = incoming.source_url
  )
  returning id, clinic_id, source_url, source_title, source_type, retrieved_at, metadata
)
select jsonb_build_object(
  'inserted', coalesce(jsonb_agg(to_jsonb(inserted) order by inserted.source_title), '[]'::jsonb),
  'inserted_count', count(*),
  'generated_at', now()
)
from inserted;
"""


def summarize(results: list[dict[str, Any]], apply: bool, inserted_count: int = 0) -> dict[str, Any]:
    items = [item for result in results for item in result.get("items", [])]
    new_items = [item for item in items if not item.get("already_stored")]
    return {
        "mode": "apply" if apply else "dry_run",
        "writes_data": bool(apply),
        "clinics_seen": len(results),
        "failed_clinics": sum(1 for result in results if result.get("status") == "failed"),
        "team_sources_found": len(items),
        "new_team_sources": len(new_items),
        "already_stored": len(items) - len(new_items),
        "inserted_count": inserted_count,
        "items": items,
        "safety": "stores source_records only; does not edit profiles, resolve reviews or publish the website",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--clinic-slug", help="Discover team sources for one clinic.")
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--max-links-per-clinic", type=int, default=MAX_LINKS_PER_CLINIC)
    parser.add_argument("--apply", action="store_true", help="Store discovered source_records. Never edits clinics.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1.")
    if args.timeout < 3 or args.timeout > 60:
        raise SystemExit("--timeout must be between 3 and 60 seconds.")
    if args.max_links_per_clinic < 1 or args.max_links_per_clinic > 8:
        raise SystemExit("--max-links-per-clinic must be between 1 and 8.")

    local_env = load_env_file()
    clinics = load_visible_clinics(args.limit, args.clinic_slug, local_env)
    results = [
        discover_for_clinic(clinic, args.timeout, args.max_links_per_clinic, local_env)
        for clinic in clinics
    ]
    new_rows = [
        item
        for result in results
        for item in result.get("items", [])
        if not item.get("already_stored")
    ]
    inserted_count = 0
    if args.apply and new_rows:
        inserted = json.loads(run_psql(insert_sources_sql(new_rows), local_env) or "{}")
        inserted_count = int(inserted.get("inserted_count") or 0)
    print(json.dumps(summarize(results, args.apply, inserted_count), ensure_ascii=False, indent=2))
    return 0 if not any(result.get("status") == "failed" for result in results) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
