#!/usr/bin/env python3
"""Shared conservative rules for clinic Google Maps profile links."""
from __future__ import annotations


GOOGLE_MAPS_PROFILE_KEYS = ("maps_url", "google_maps_url", "map_url")


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
