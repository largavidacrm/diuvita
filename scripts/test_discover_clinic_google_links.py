#!/usr/bin/env python3
"""Checks for Google Maps/review link discovery."""

from argparse import Namespace

from capture_source_snapshot import FetchResult
from discover_clinic_google_links import (
    best_links,
    discover_google_links,
    process_clinic,
    review_payload,
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    html = """
<!doctype html>
<html>
<body>
  <a href="https://www.google.com/maps/place/Example+Longevity+Clinic/">Google Maps</a>
  <a href="https://search.google.com/local/writereview?placeid=abc123">Escribir reseña</a>
  <a href="https://g.page/example-longevity-clinic/review">Reseñas en Google</a>
  <iframe src="https://www.google.com/maps/embed?pb=abc" title="Mapa"></iframe>
</body>
</html>
"""
    candidates = discover_google_links("https://exampleclinic.test/", html)
    links = best_links(candidates)
    check(links["maps_url"].startswith("https://www.google.com/maps/place/"), "profile Maps link missing")
    check("review" in links["google_reviews_url"].lower(), "Google review link missing")
    noisy = discover_google_links(
        "https://exampleclinic.test/",
        """
        <a href="https://www.google.com/maps/dir/?api=1&destination=40.1,-3.2">Cómo llegar</a>
        <a href="https://maps.google.com/maps?q=Example+Clinic+Madrid">Mapa</a>
        <a href="https://www.google.com/maps/contrib/101/reviews">Laura</a>
        <iframe src="https://www.google.com/maps/embed?pb=abc" title="Mapa"></iframe>
        """,
    )
    check(not noisy, "directions, embeds, generic searches and contributor reviews should be ignored")

    clinic = {
        "clinic_id": "clinic-1",
        "slug": "example-clinic",
        "display_name": "Example Longevity Clinic",
        "city": "Madrid",
        "country": "España",
        "website": "https://exampleclinic.test",
        "has_google_maps": False,
        "has_google_reviews": False,
    }
    args = Namespace(
        timeout=15,
        apply=False,
        replace_existing=False,
        allow_multiple_open_clinic_reviews=False,
    )

    def fake_fetcher(url, timeout):
        return FetchResult(
            source_url=url,
            final_url=url,
            status_code=200,
            content_type="text/html; charset=utf-8",
            body=html.encode("utf-8"),
        )

    created = []

    def fake_review_creator(*_args):
        created.append(_args)
        return {"status": "inserted", "id": "review-1"}

    dry_run = process_clinic(clinic, args, "admin@example.test", {}, fake_fetcher, fake_review_creator)
    check(dry_run["status"] == "ready", "clinic should be ready when Google links are detected")
    check(dry_run["proposed_fields"]["maps_url"] == links["maps_url"], "maps_url proposal missing")
    check(dry_run["proposed_fields"]["google_reviews_url"] == links["google_reviews_url"], "reviews proposal missing")
    check(not created, "dry-run should not create review cards")

    ambiguous_html = """
    <a href="https://www.google.com/maps/place/?q=place_id:one">Laura</a>
    <a href="https://www.google.com/maps/place/?q=place_id:two">Marta</a>
    """

    def fake_ambiguous_fetcher(url, timeout):
        return FetchResult(
            source_url=url,
            final_url=url,
            status_code=200,
            content_type="text/html; charset=utf-8",
            body=ambiguous_html.encode("utf-8"),
        )

    ambiguous = process_clinic(clinic, args, "admin@example.test", {}, fake_ambiguous_fetcher, fake_review_creator)
    check(ambiguous["status"] == "empty", "ambiguous equal Google links should not be auto-proposed")

    payload = review_payload(clinic, clinic["website"], dry_run["proposed_fields"], candidates)
    check(payload["mode"] == "shadow", "payload should stay in shadow mode")
    check(payload["proposed_fields"]["maps_url"] == links["maps_url"], "payload Maps link missing")
    check("confirmar" in payload["warnings"][0], "human-review warning missing")

    args.apply = True
    applied = process_clinic(clinic, args, "admin@example.test", {}, fake_fetcher, fake_review_creator)
    check(applied["created_review"]["status"] == "inserted", "apply mode should create a review card")
    check(created, "review creator should be called in apply mode")

    already_complete = dict(clinic, has_google_maps=True, has_google_reviews=True)
    complete = process_clinic(already_complete, args, "admin@example.test", {}, fake_fetcher, fake_review_creator)
    check(complete["status"] == "empty", "complete clinic should not propose duplicate Google links")
    print("OK Google links: discovery creates review-ready proposals")


if __name__ == "__main__":
    main()
