#!/usr/bin/env python3
"""Checks for shared Google Maps profile URL SQL rules."""

from google_maps_url_rules import google_maps_profile_link_predicate, google_maps_profile_url_sql


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    url_check = google_maps_profile_url_sql("candidate_url")
    link_check = google_maps_profile_link_predicate("maps_url", "google_maps_url", "map_url")

    check("/maps/place/" in url_check, "direct place URLs should be accepted")
    check("place_id:" in url_check, "place_id query URLs should be accepted")
    check("placeid=" in url_check, "placeid query URLs should be accepted")
    check("query_place_id=" in url_check, "query_place_id URLs should be accepted")
    check("cid=" in url_check, "cid URLs should be accepted")
    check("maps.app.goo.gl" in url_check, "Google short place links should be accepted")
    check("/maps/search" in url_check, "generic Maps search URLs should be rejected")
    check("/maps/dir" in url_check, "directions URLs should be rejected")
    check("google.com/search" in url_check, "generic Google search URLs should be rejected")
    check("calle|c/|avenida" in url_check, "street-address place URLs should be guarded")
    check("c.current_data ->> 'map_url'" in link_check, "top-level map_url should be checked")
    check("location.value ->> 'map_url'" in link_check, "location map_url should be checked")
    print("OK Google Maps URL rules: profile-only SQL guard present")


if __name__ == "__main__":
    main()
