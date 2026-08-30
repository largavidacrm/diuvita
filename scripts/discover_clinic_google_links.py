#!/usr/bin/env python3
"""Discover official Google Maps/review links for visible Vitalarga clinics.

Default mode is dry-run. Apply mode creates internal clinic_profile_enrichment
review cards only; it never edits clinic profiles, resolves reviews, or
publishes public pages.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, unquote, urldefrag, urljoin, urlparse

from capture_source_snapshot import FetchResult, decode_body, fetch_url, normalize_space
from submit_discovery_candidates import get_default_admin_email, load_env_file, run_psql, sql_literal
from submit_shadow_extraction_review import create_review


DISCOVERER_NAME = "vitalarga-google-link-discoverer"
DISCOVERER_VERSION = "2026-08-30"

REVIEW_TERMS = (
    "review",
    "reviews",
    "writereview",
    "reseña",
    "reseñas",
    "valoracion",
    "valoraciones",
    "opiniones",
)
LOW_SIGNAL_NAME_TERMS = {
    "clinic",
    "clinica",
    "clínica",
    "medical",
    "medicina",
    "longevity",
    "longevidad",
    "salud",
    "unidad",
}
ADDRESS_LABEL_RE = re.compile(
    r"\b(c/|calle|avenida|av\.|avda\.|paseo|passeig|plaça|plaza|ronda|carretera|road|street)\b|\b\d{5}\b|\d",
    flags=re.I,
)
SECONDARY_PAGE_TERMS = (
    "contacto",
    "contact",
    "ubicacion",
    "ubicación",
    "donde estamos",
    "dónde estamos",
    "como llegar",
    "cómo llegar",
    "localizacion",
    "localización",
    "sede",
    "sedes",
    "centro",
    "centros",
    "mapa",
    "maps",
    "location",
    "locations",
    "visit",
)


@dataclass(frozen=True)
class GoogleLinkCandidate:
    url: str
    label: str
    kind: str
    score: int
    source_tag: str


class GoogleLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str, str]] = []
        self._href: str | None = None
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr_map = dict(attrs)
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if tag == "a" and not self._skip_depth:
            self._href = attr_map.get("href") or ""
            self._parts = []
        if tag == "iframe" and not self._skip_depth:
            src = attr_map.get("src") or ""
            if src:
                self.links.append((src, attr_map.get("title") or "", "iframe"))

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "a" and self._href is not None:
            self.links.append((self._href, normalize_space(" ".join(self._parts)), "a"))
            self._href = None
            self._parts = []
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._href is None or self._skip_depth:
            return
        clean = normalize_space(data)
        if clean:
            self._parts.append(clean)


FetchFn = Callable[..., FetchResult]
CreateReviewFn = Callable[[str, dict[str, Any], str, dict[str, str], bool, bool], dict[str, Any]]


def today_batch() -> str:
    return "google-link-discovery-" + datetime.now(timezone.utc).date().isoformat()


def fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return normalized.encode("ascii", "ignore").decode("ascii").lower()


def google_host(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def clean_google_url(base_url: str, href: str) -> str:
    raw = normalize_space(unquote(href or ""))
    if not raw or raw.startswith(("#", "mailto:", "tel:", "javascript:")):
        return ""
    absolute = urljoin(base_url, raw)
    absolute, _fragment = urldefrag(absolute)
    parsed = urlparse(absolute)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    host = google_host(absolute)
    if not (
        host == "maps.app.goo.gl"
        or host == "g.page"
        or host == "goo.gl"
        or host.endswith("google.com")
        or ".google." in host
    ):
        return ""
    return parsed.geturl()


def clean_same_site_url(base_url: str, href: str) -> str:
    raw = normalize_space(unquote(href or ""))
    if not raw or raw.startswith(("#", "mailto:", "tel:", "javascript:")):
        return ""
    absolute = urljoin(base_url, raw)
    absolute, _fragment = urldefrag(absolute)
    parsed = urlparse(absolute)
    base = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    if google_host(parsed.geturl()) != google_host(base.geturl()):
        return ""
    path = parsed.path or "/"
    if path == "/" or re.search(r"\.(pdf|jpg|jpeg|png|webp|gif|svg|zip|docx?|xlsx?)$", path, flags=re.I):
        return ""
    return parsed.geturl()


def secondary_page_score(url: str, label: str) -> int:
    parsed = urlparse(url)
    haystack = fold(" ".join([parsed.path.replace("-", " "), parsed.query.replace("-", " "), label]))
    score = 0
    for term in SECONDARY_PAGE_TERMS:
        if fold(term) in haystack:
            score += 10
    if any(skip in haystack for skip in ("blog", "noticia", "news", "privacy", "privacidad", "cookies")):
        score -= 20
    return score


def discover_secondary_pages(base_url: str, html_text: str, max_pages: int = 3) -> list[str]:
    if max_pages <= 0:
        return []
    parser = GoogleLinkParser()
    parser.feed(html_text)
    scored: dict[str, int] = {}
    for href, label, source_tag in parser.links:
        if source_tag != "a":
            continue
        url = clean_same_site_url(base_url, href)
        if not url:
            continue
        score = secondary_page_score(url, label)
        if score <= 0:
            continue
        scored[url] = max(score, scored.get(url, 0))
    return [
        url
        for url, _score in sorted(scored.items(), key=lambda item: (-item[1], item[0]))[:max_pages]
    ]


def looks_like_google_maps_url(url: str) -> bool:
    parsed = urlparse(url)
    host = google_host(url)
    haystack = fold(" ".join([host, parsed.path, parsed.query]))
    path = parsed.path.lower()
    if "/maps/embed" in path or "/maps/dir" in path or "/maps/contrib/" in path:
        return False
    query = parse_qs(parsed.query)
    if any(key in query for key in ("daddr", "destination")) and not any(key in query for key in ("cid", "placeid")):
        return False
    if host in {"maps.app.goo.gl", "g.page"}:
        return True
    if host == "goo.gl" and parsed.path.lower().startswith("/maps"):
        return True
    if "google" not in host:
        return False
    if "/place" in path:
        return True
    return any(key in query for key in ("cid", "placeid")) or "place_id:" in haystack


def classify_google_link(url: str, label: str, source_tag: str) -> GoogleLinkCandidate | None:
    if not looks_like_google_maps_url(url):
        return None
    haystack = fold(" ".join([url, label]))
    is_review = any(term in haystack for term in REVIEW_TERMS)
    score = 10
    if "/place/" in urlparse(url).path.lower():
        score += 10
    if "maps.app.goo.gl" in google_host(url):
        score += 8
    if source_tag == "a":
        score += 4
    if label:
        score += 2
    if is_review:
        score += 12
    return GoogleLinkCandidate(
        url=url,
        label=label,
        kind="google_reviews_url" if is_review else "maps_url",
        score=score,
        source_tag=source_tag,
    )


def discover_google_links(base_url: str, html_text: str) -> list[GoogleLinkCandidate]:
    parser = GoogleLinkParser()
    parser.feed(html_text)
    by_kind_and_url: dict[tuple[str, str], GoogleLinkCandidate] = {}
    for href, label, source_tag in parser.links:
        url = clean_google_url(base_url, href)
        if not url:
            continue
        candidate = classify_google_link(url, label, source_tag)
        if not candidate:
            continue
        key = (candidate.kind, candidate.url)
        existing = by_kind_and_url.get(key)
        if not existing or candidate.score > existing.score:
            by_kind_and_url[key] = candidate
    return sorted(by_kind_and_url.values(), key=lambda item: (item.kind, -item.score, item.url))


def dedupe_google_candidates(candidates: list[GoogleLinkCandidate]) -> list[GoogleLinkCandidate]:
    by_kind_and_url: dict[tuple[str, str], GoogleLinkCandidate] = {}
    for candidate in candidates:
        key = (candidate.kind, candidate.url)
        existing = by_kind_and_url.get(key)
        if not existing or candidate.score > existing.score:
            by_kind_and_url[key] = candidate
    return sorted(by_kind_and_url.values(), key=lambda item: (item.kind, -item.score, item.url))


def clinic_name_terms(clinic: dict[str, Any] | None) -> list[str]:
    if not clinic:
        return []
    raw_terms = [
        fold(str(clinic.get("display_name") or clinic.get("clinic_name") or "")),
        fold(str(clinic.get("slug") or "")).replace("-", " "),
    ]
    terms: list[str] = []
    for raw in raw_terms:
        if raw and raw not in terms:
            terms.append(raw)
        for part in re.split(r"[^a-z0-9]+", raw):
            if len(part) >= 4 and part not in LOW_SIGNAL_NAME_TERMS and part not in terms:
                terms.append(part)
    return terms


def context_terms(clinic: dict[str, Any] | None) -> list[str]:
    terms = clinic_name_terms(clinic)
    city = fold(str((clinic or {}).get("city") or ""))
    if city and city not in terms:
        terms.append(city)
    return terms


def context_score(candidate: GoogleLinkCandidate, clinic: dict[str, Any] | None) -> int:
    haystack = fold(" ".join([candidate.url, candidate.label]))
    return sum(1 for term in context_terms(clinic) if term and term in haystack)


def clinic_name_score(candidate: GoogleLinkCandidate, clinic: dict[str, Any] | None) -> int:
    haystack = fold(" ".join([candidate.url, candidate.label]))
    return sum(1 for term in clinic_name_terms(clinic) if term and term in haystack)


def has_direct_place_identifier(candidate: GoogleLinkCandidate) -> bool:
    parsed = urlparse(candidate.url)
    host = google_host(candidate.url)
    query = parse_qs(parsed.query)
    haystack = fold(" ".join([parsed.path, parsed.query]))
    return bool(
        host in {"maps.app.goo.gl", "g.page"} or
        (host == "goo.gl" and parsed.path.lower().startswith("/maps")) or
        any(key in query for key in ("cid", "placeid", "query_place_id")) or
        "place_id:" in haystack
    )


def looks_like_address_label(label: str) -> bool:
    return bool(ADDRESS_LABEL_RE.search(label or ""))


def best_links(candidates: list[GoogleLinkCandidate], clinic: dict[str, Any] | None = None) -> dict[str, str]:
    result: dict[str, str] = {}
    for kind in ("maps_url", "google_reviews_url"):
        matches = [candidate for candidate in candidates if candidate.kind == kind]
        if matches:
            ranked = sorted(
                matches,
                key=lambda item: (-(item.score + context_score(item, clinic) * 12), item.url),
            )
            if len(ranked) > 1:
                top = ranked[0]
                second = ranked[1]
                top_score = top.score + context_score(top, clinic) * 12
                second_score = second.score + context_score(second, clinic) * 12
                if clinic and top_score == second_score and not context_score(top, clinic):
                    continue
            if (
                clinic
                and kind == "maps_url"
                and not clinic_name_score(ranked[0], clinic)
                and (looks_like_address_label(ranked[0].label) or not has_direct_place_identifier(ranked[0]))
            ):
                continue
            result[kind] = ranked[0].url
    return result


def direct_link_predicate(*keys: str) -> str:
    root_values = ", ".join(f"c.current_data ->> '{key}'" for key in keys)
    location_values = ",\n          ".join(f"location.value ->> '{key}'" for key in keys)
    return f"""
    (
      nullif(btrim(coalesce({root_values}, '')), '') is not null
      or exists (
        select 1
        from jsonb_array_elements(
          case
            when jsonb_typeof(c.current_data -> 'locations') = 'array'
              then c.current_data -> 'locations'
            else '[]'::jsonb
          end
        ) as location(value)
        where nullif(btrim(coalesce(
          {location_values},
          ''
        )), '') is not null
      )
    )
"""


def load_visible_clinics(limit: int, clinic_slug: str | None, local_env: dict[str, str]) -> list[dict[str, Any]]:
    clinic_filter = f"and c.slug = {sql_literal(clinic_slug)}" if clinic_slug else ""
    has_google_maps = direct_link_predicate("maps_url", "google_maps_url", "map_url")
    has_google_reviews = direct_link_predicate("google_reviews_url", "reviews_url", "valoraciones_url")
    sql = f"""
with visible as (
  select
    c.id as clinic_id,
    c.slug,
    c.display_name,
    c.city,
    c.country,
    c.status,
    c.website,
    {has_google_maps} as has_google_maps,
    {has_google_reviews} as has_google_reviews,
    case when c.status = 'published' then 0 else 1 end as status_order
  from public.clinics c
  where c.status in ('published', 'preliminary')
    and c.website ~* '^https?://'
    {clinic_filter}
)
select coalesce(jsonb_agg(to_jsonb(items) order by items.status_order, items.display_name), '[]'::jsonb)
from (
  select *
  from visible
  where not has_google_maps or not has_google_reviews
  order by status_order, display_name
  limit {max(1, min(100, int(limit)))}
) items;
"""
    return json.loads(run_psql(sql, local_env) or "[]")


def review_payload(
    clinic: dict[str, Any],
    source_url: str,
    proposed_fields: dict[str, str],
    candidates: list[GoogleLinkCandidate],
    source_urls: list[str] | None = None,
) -> dict[str, Any]:
    urls = list(dict.fromkeys(source_urls or [source_url]))
    return {
        "mode": "shadow",
        "proposal_batch": today_batch(),
        "discoverer": DISCOVERER_NAME,
        "discoverer_version": DISCOVERER_VERSION,
        "clinic_slug": clinic.get("slug"),
        "clinic_name": clinic.get("display_name"),
        "clinic_city": clinic.get("city"),
        "clinic_country": clinic.get("country"),
        "source_url": source_url,
        "source_urls": urls,
        "warnings": [
            "Enlaces de Google detectados desde la web oficial o páginas internas de contacto/sedes; confirmar que abren la ficha correcta antes de guardar."
        ],
        "proposed_fields": proposed_fields,
        "google_link_candidates": [asdict(candidate) for candidate in candidates],
    }


def process_clinic(
    clinic: dict[str, Any],
    args: argparse.Namespace,
    admin_email: str,
    local_env: dict[str, str],
    fetcher: FetchFn = fetch_url,
    review_creator: CreateReviewFn = create_review,
) -> dict[str, Any]:
    website = str(clinic.get("website") or "")
    result = {
        "clinic_id": clinic.get("clinic_id"),
        "clinic_slug": clinic.get("slug"),
        "clinic_name": clinic.get("display_name"),
        "website": website,
        "has_google_maps": bool(clinic.get("has_google_maps")),
        "has_google_reviews": bool(clinic.get("has_google_reviews")),
    }
    if not website:
        return {**result, "status": "skipped", "reason": "missing website"}

    try:
        fetch_result = fetcher(website.rstrip("/") + "/", timeout=args.timeout)
        html_text = decode_body(fetch_result.body, fetch_result.content_type)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as error:
        return {**result, "status": "failed", "error": str(error)}

    source_url = fetch_result.final_url or website
    scanned_urls = [source_url]
    candidates = discover_google_links(source_url, html_text)
    fetch_errors = []
    for page_url in discover_secondary_pages(
        source_url,
        html_text,
        max_pages=max(0, int(getattr(args, "max_secondary_pages", 3) or 0)),
    ):
        if page_url in scanned_urls:
            continue
        try:
            page_result = fetcher(page_url, timeout=args.timeout)
            page_final_url = page_result.final_url or page_url
            page_html = decode_body(page_result.body, page_result.content_type)
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as error:
            fetch_errors.append({"url": page_url, "error": str(error)})
            continue
        scanned_urls.append(page_final_url)
        candidates.extend(discover_google_links(page_final_url, page_html))
    candidates = dedupe_google_candidates(candidates)
    links = best_links(candidates, clinic)
    proposed_fields = {}
    if not clinic.get("has_google_maps") and links.get("maps_url"):
        proposed_fields["maps_url"] = links["maps_url"]
    if not clinic.get("has_google_reviews") and links.get("google_reviews_url"):
        proposed_fields["google_reviews_url"] = links["google_reviews_url"]

    result.update({
        "status": "ready" if proposed_fields else "empty",
        "proposed_fields": proposed_fields,
        "google_link_candidates": [asdict(candidate) for candidate in candidates],
        "scanned_urls": scanned_urls,
        "fetch_errors": fetch_errors,
    })
    if args.apply and proposed_fields:
        payload = review_payload(clinic, source_url, proposed_fields, candidates, scanned_urls)
        result["created_review"] = review_creator(
            str(clinic.get("slug") or ""),
            payload,
            admin_email,
            local_env,
            args.replace_existing,
            args.allow_multiple_open_clinic_reviews,
        )
    return result


def summarize(results: list[dict[str, Any]], apply: bool) -> dict[str, Any]:
    return {
        "mode": "apply" if apply else "dry_run",
        "writes_data": bool(apply),
        "clinics_seen": len(results),
        "ready": sum(1 for item in results if item.get("status") == "ready"),
        "empty": sum(1 for item in results if item.get("status") == "empty"),
        "failed": sum(1 for item in results if item.get("status") == "failed"),
        "maps_links_found": sum(1 for item in results if (item.get("proposed_fields") or {}).get("maps_url")),
        "review_links_found": sum(1 for item in results if (item.get("proposed_fields") or {}).get("google_reviews_url")),
        "items": results,
        "safety": "creates review cards only; does not edit clinic profiles, resolve reviews or publish the website",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--clinic-slug", help="Discover Google links for one clinic.")
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--max-secondary-pages", type=int, default=3, help="Scan this many same-site contact/location pages in addition to the home page.")
    parser.add_argument("--admin-email", help="Admin email assigned to created review cards.")
    parser.add_argument("--replace-existing", action="store_true", help="Refresh an existing open review for the same source.")
    parser.add_argument(
        "--allow-multiple-open-clinic-reviews",
        action="store_true",
        help="Allow more than one open enrichment card for the same clinic.",
    )
    parser.add_argument("--apply", action="store_true", help="Create internal review cards. Never edits clinics.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1.")
    if args.timeout < 3 or args.timeout > 60:
        raise SystemExit("--timeout must be between 3 and 60 seconds.")
    if args.max_secondary_pages < 0 or args.max_secondary_pages > 5:
        raise SystemExit("--max-secondary-pages must be between 0 and 5.")

    local_env = load_env_file()
    admin_email = args.admin_email or get_default_admin_email(local_env)
    clinics = load_visible_clinics(args.limit, args.clinic_slug, local_env)
    results = [
        process_clinic(clinic, args, admin_email, local_env)
        for clinic in clinics
    ]
    output = summarize(results, args.apply)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["failed"] == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
