#!/usr/bin/env python3
"""Checks for Google Maps/review link discovery."""

from argparse import Namespace
from pathlib import Path

from capture_source_snapshot import FetchResult
from discover_clinic_google_links import (
    best_links,
    compact_summary,
    dedupe_google_candidates,
    discover_google_links,
    discover_secondary_pages,
    has_direct_place_identifier,
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

    address_only = discover_google_links(
        "https://exampleclinic.test/",
        '<a href="https://www.google.com/maps/place//data=!4m2!3m1!1s0xabc:0xdef">C/ Claudio Coello 19, 28001 Madrid</a>',
    )
    check(not best_links(address_only, clinic={
        "display_name": "Example Longevity Clinic",
        "slug": "example-clinic",
        "city": "Madrid",
    }), "address-only Maps links should not be proposed as clinic profiles")

    named_place = discover_google_links(
        "https://exampleclinic.test/",
        '<a href="https://www.google.com/maps/place/Example+Longevity+Clinic/">C/ Claudio Coello 19, 28001 Madrid</a>',
    )
    check(best_links(named_place, clinic={
        "display_name": "Example Longevity Clinic",
        "slug": "example-clinic",
        "city": "Madrid",
    })["maps_url"].startswith("https://www.google.com/maps/place/Example+Longevity+Clinic/"), "named Maps profiles should still be proposed")
    check(len(dedupe_google_candidates(named_place + named_place)) == 1, "duplicate candidates should be collapsed")

    generic_label_address_place = discover_google_links(
        "https://exampleclinic.test/",
        '<a href="https://www.google.com/maps/place/Calle+Sagasta+8,+Malaga">Google Maps</a>',
    )
    check(not best_links(generic_label_address_place, clinic={
        "display_name": "Example Longevity Clinic",
        "slug": "example-clinic",
        "city": "Málaga",
    }), "generic-label address place URLs should not be proposed as clinic profiles")

    place_id_link = discover_google_links(
        "https://exampleclinic.test/",
        '<a href="https://www.google.com/maps/place/?q=place_id:abc123">Google Maps</a>',
    )
    check(has_direct_place_identifier(place_id_link[0]), "place-id links should be treated as direct place identifiers")
    check(best_links(place_id_link, clinic={
        "display_name": "Example Longevity Clinic",
        "slug": "example-clinic",
        "city": "Madrid",
    })["maps_url"].startswith("https://www.google.com/maps/place/"), "place-id Maps links should still be proposed")

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

    secondary_pages = discover_secondary_pages(
        "https://exampleclinic.test/",
        """
        <a href="/blog/longevidad">Blog</a>
        <a href="/contacto/">Contacto</a>
        <a href="/donde-estamos/">Dónde estamos</a>
        """,
        max_pages=2,
    )
    check(secondary_pages == [
        "https://exampleclinic.test/contacto/",
        "https://exampleclinic.test/donde-estamos/",
    ], "contact/location pages should be selected before noisy links")

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
        max_secondary_pages=3,
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

    contact_home = """
<!doctype html>
<html><body><a href="/contacto/">Contacto y ubicación</a></body></html>
"""
    contact_page = """
<!doctype html>
<html><body><a href="https://www.google.com/maps/place/Example+Longevity+Clinic/">Google Maps</a></body></html>
"""

    def fake_contact_fetcher(url, timeout):
        body = contact_page if url.rstrip("/").endswith("/contacto") else contact_home
        return FetchResult(
            source_url=url,
            final_url=url,
            status_code=200,
            content_type="text/html; charset=utf-8",
            body=body.encode("utf-8"),
        )

    contact_result = process_clinic(clinic, args, "admin@example.test", {}, fake_contact_fetcher, fake_review_creator)
    check(contact_result["status"] == "ready", "contact page should produce a Google link proposal")
    check(contact_result["proposed_fields"]["maps_url"].startswith("https://www.google.com/maps/place/"), "contact page Maps proposal missing")
    check("https://exampleclinic.test/contacto/" in contact_result["scanned_urls"], "secondary contact page should be scanned")

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

    payload = review_payload(clinic, clinic["website"], dry_run["proposed_fields"], candidates, dry_run["scanned_urls"])
    check(payload["mode"] == "shadow", "payload should stay in shadow mode")
    check(payload["proposed_fields"]["maps_url"] == links["maps_url"], "payload Maps link missing")
    check("confirmar" in payload["warnings"][0], "human-review warning missing")
    check(payload["source_urls"] == dry_run["scanned_urls"], "payload should preserve scanned official URLs")

    args.apply = True
    applied = process_clinic(clinic, args, "admin@example.test", {}, fake_fetcher, fake_review_creator)
    check(applied["created_review"]["status"] == "inserted", "apply mode should create a review card")
    check(created, "review creator should be called in apply mode")

    compact = compact_summary({
        "mode": "dry_run",
        "writes_data": False,
        "clinics_seen": 2,
        "ready": 1,
        "empty": 1,
        "failed": 0,
        "maps_links_found": 1,
        "review_links_found": 0,
        "items": [
            dry_run,
            {
                "clinic_slug": "address-only",
                "clinic_name": "Address Only",
                "status": "empty",
                "proposed_fields": {},
                "scanned_urls": ["https://address-only.example/"],
                "google_link_candidates": [{"url": "https://www.google.com/maps/place/Calle+1"}],
                "fetch_errors": [],
            },
        ],
        "safety": "safe",
    })
    check(compact["ready_items"][0]["clinic_slug"] == "example-clinic", "compact ready item missing")
    check(compact["empty_with_candidates"][0]["clinic_slug"] == "address-only", "compact empty candidate item missing")
    check("google_link_candidates" not in compact["ready_items"][0], "compact output should omit full candidates")

    already_complete = dict(clinic, has_google_maps=True, has_google_reviews=True)
    complete = process_clinic(already_complete, args, "admin@example.test", {}, fake_fetcher, fake_review_creator)
    check(complete["status"] == "empty", "complete clinic should not propose duplicate Google links")

    source = (Path(__file__).resolve().parents[1] / "scripts" / "discover_clinic_google_links.py").read_text(encoding="utf-8")
    check("google_maps_profile_link_predicate" in source, "clinic loader should use direct-only Maps SQL rule")
    print("OK Google links: discovery creates review-ready proposals")


if __name__ == "__main__":
    main()
