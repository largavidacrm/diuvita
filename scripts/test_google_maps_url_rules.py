#!/usr/bin/env python3
"""Checks for shared Google Maps profile URL rules."""

from google_maps_url_rules import (
    google_maps_profile_link_predicate,
    google_maps_profile_url_sql,
    google_maps_review_status,
    is_direct_google_maps_profile_url,
    is_google_maps_like_url,
)


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
    check(is_google_maps_like_url("https://www.google.com/maps/place/Clinic+A/"), "Google Maps URL should be recognized")
    check(is_direct_google_maps_profile_url("https://www.google.com/maps/place/Clinic+A/"), "named place URL should be accepted")
    check(is_direct_google_maps_profile_url("https://www.google.com/maps?cid=12345"), "cid URL should be accepted")
    check(not is_direct_google_maps_profile_url("https://www.google.com/maps/search/Clinic+A"), "search URL should be rejected")
    check(not is_direct_google_maps_profile_url("https://www.google.com/maps/dir/Clinic+A"), "route URL should be rejected")
    check(not is_direct_google_maps_profile_url("https://www.google.com/maps/place/Calle+Serrano+100,+Madrid"), "street-address URL should be rejected")
    check(google_maps_review_status("") == "empty", "empty Maps status missing")
    check(google_maps_review_status("https://example.test") == "not_google_maps", "non-Google Maps status missing")
    check(google_maps_review_status("https://www.google.com/maps/search/Clinic+A") == "search_or_route", "search status missing")
    check(google_maps_review_status("https://www.google.com/maps/place/Calle+Serrano+100,+Madrid") == "street_address", "street-address status missing")
    check(google_maps_review_status("https://www.google.com/maps/place/Clinic+A/") == "direct_profile", "direct profile status missing")
    print("OK Google Maps URL rules: profile-only SQL guard present")


if __name__ == "__main__":
    main()
