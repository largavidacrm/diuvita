#!/usr/bin/env python3
"""Shared conservative rules for clinic Google Maps profile links."""
from __future__ import annotations

import re
from urllib.parse import unquote_plus, urlparse


GOOGLE_MAPS_PROFILE_KEYS = ("maps_url", "google_maps_url", "map_url")
ADDRESS_MAP_RE = re.compile(
    r"/maps/place/(calle|c/|avenida|av\.|avda\.?|paseo|passeig|plaza|ronda|carretera|road|street|carrer|camino|via)([\s,./-]|$)",
    flags=re.I,
)


def decoded_url(value: object) -> str:
    if not isinstance(value, str):
        return ""
    try:
        return unquote_plus(value).strip().lower()
    except Exception:
        return value.strip().lower()


def is_google_maps_like_url(value: object) -> bool:
    clean = decoded_url(value)
    return bool(
        ("google." in clean and "/maps" in clean)
        or "maps.app.goo.gl" in clean
        or "goo.gl/maps" in clean
        or "g.page/" in clean
    )


def is_direct_google_maps_profile_url(value: object) -> bool:
    clean = decoded_url(value)
    if not clean:
        return False
    if not is_google_maps_like_url(clean):
        return False
    if any(marker in clean for marker in ("/maps/search", "/maps/dir", "google.com/search")):
        return False
    if ("?q=" in clean or "&q=" in clean or "?query=" in clean or "&query=" in clean) and "place_id:" not in clean:
        return False
    if ADDRESS_MAP_RE.search(clean):
        return False
    return any(
        marker in clean
        for marker in (
            "/maps/place/",
            "place_id:",
            "placeid=",
            "place_id=",
            "query_place_id=",
            "cid=",
            "ftid=",
            "maps.app.goo.gl",
            "goo.gl/maps",
            "g.page/",
        )
    )


def google_maps_review_status(value: object) -> str:
    clean = decoded_url(value)
    if not clean:
        return "empty"
    if not is_google_maps_like_url(clean):
        return "not_google_maps"
    if is_direct_google_maps_profile_url(clean):
        return "direct_profile"
    if "/maps/search" in clean or "/maps/dir" in clean or "google.com/search" in clean:
        return "search_or_route"
    if ADDRESS_MAP_RE.search(clean):
        return "street_address"
    return "needs_manual_review"


def google_maps_profile_url_sql(value_sql: str) -> str:
    """Return SQL that treats only strong clinic-profile Maps URLs as present."""
    normalized = f"lower(replace(replace(coalesce({value_sql}, ''), '+', ' '), '%20', ' '))"
    return f"""(
      {normalized} <> ''
      and (
        ({normalized} like '%google.%' and {normalized} like '%/maps%')
        or {normalized} like '%maps.app.goo.gl%'
        or {normalized} like '%goo.gl/maps%'
        or {normalized} like '%g.page/%'
      )
      and (
        {normalized} like '%/maps/place/%'
        or {normalized} like '%place_id:%'
        or {normalized} like '%placeid=%'
        or {normalized} like '%place_id=%'
        or {normalized} like '%query_place_id=%'
        or {normalized} like '%cid=%'
        or {normalized} like '%ftid=%'
        or {normalized} like '%maps.app.goo.gl%'
        or {normalized} like '%goo.gl/maps%'
        or {normalized} like '%g.page/%'
      )
      and {normalized} not like '%/maps/search%'
      and {normalized} not like '%/maps/dir%'
      and {normalized} not like '%google.com/search%'
      and {normalized} !~ '/maps/place/(calle|c/|avenida|av[.]|avda[.]?|paseo|passeig|plaza|ronda|carretera|road|street|carrer|camino|via)([[:space:],./-]|$)'
    )"""


def coalesced_jsonb_text_sql(owner_sql: str, keys: tuple[str, ...]) -> str:
    values = ", ".join(f"{owner_sql} ->> '{key}'" for key in keys)
    return f"coalesce({values}, '')"


def google_maps_profile_link_predicate(*keys: str) -> str:
    """Return SQL checking top-level and per-location Google Maps profile links."""
    checked_keys = tuple(keys or GOOGLE_MAPS_PROFILE_KEYS)
    root_check = google_maps_profile_url_sql(coalesced_jsonb_text_sql("c.current_data", checked_keys))
    location_check = google_maps_profile_url_sql(coalesced_jsonb_text_sql("location.value", checked_keys))
    return f"""
    (
      {root_check}
      or exists (
        select 1
        from jsonb_array_elements(
          case
            when jsonb_typeof(c.current_data -> 'locations') = 'array'
              then c.current_data -> 'locations'
            else '[]'::jsonb
          end
        ) as location(value)
        where {location_check}
      )
    )
"""
