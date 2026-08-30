#!/usr/bin/env python3
"""Checks for static data validation rules."""

from validate_data import is_direct_google_maps_profile_url, validate_google_maps_value


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    direct_urls = [
        "https://www.google.com/maps/place/Vitalarga+Clinic/",
        "https://www.google.com/maps/place/?q=place_id:abc123",
        "https://www.google.com/maps?cid=1234567890",
        "https://maps.app.goo.gl/abc123",
    ]
    rejected_urls = [
        "https://www.google.com/maps/search/?api=1&query=Calle+Serrano+100",
        "https://www.google.com/maps/dir/?api=1&destination=40.1,-3.2",
        "https://www.google.com/maps/place/Calle+Serrano+100,+Madrid",
        "https://www.google.com/search?q=clinic+maps",
    ]

    for url in direct_urls:
        check(is_direct_google_maps_profile_url(url), f"direct Google Maps profile should pass: {url}")

    for url in rejected_urls:
        check(not is_direct_google_maps_profile_url(url), f"generic/address Google Maps URL should fail: {url}")

    errors = []
    validate_google_maps_value("https://www.google.com/maps/place/Calle+Serrano+100,+Madrid", "clinic.maps_url", errors)
    check(errors, "street-address Google Maps value should add a validation error")
    check("clinic's Google Maps profile link" in errors[0], "Google Maps validation message should be explicit")
    print("OK data validation: Google Maps links must be clinic profile URLs")


if __name__ == "__main__":
    main()
