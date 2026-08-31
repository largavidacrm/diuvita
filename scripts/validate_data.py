# -*- coding: utf-8 -*-
"""Validate Vitalarga editorial data before building the static site."""
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from google_maps_url_rules import is_direct_google_maps_profile_url, is_google_maps_like_url

ROOT = Path(__file__).resolve().parents[1]
CLINICS_FILE = ROOT / "data" / "clinics.json"
LOGOS_FILE = ROOT / "data" / "logos.json"
POSTS_DIR = ROOT / "data" / "posts"

ALLOWED_STATUS = {"publicada", "preliminar"}
REQUIRED_STRINGS = ("slug", "name", "city", "country", "address", "web", "summary")
REQUIRED_LISTS = ("services", "specialties")
OPTIONAL_LISTS = ("cities_extra", "profesionales", "unidades")
OPTIONAL_STRINGS = (
    "email",
    "instagram",
    "telefono",
    "tech",
    "maps_url",
    "google_maps_url",
    "map_url",
    "google_reviews_url",
    "reviews_url",
)
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def add_error(errors, path, message):
    errors.append(f"{path}: {message}")


def is_nonempty_string(value):
    return isinstance(value, str) and bool(value.strip())


def valid_url(value):
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def load_json(path, errors):
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except Exception as exc:
        add_error(errors, str(path.relative_to(ROOT)), f"cannot read JSON ({exc})")
        return None


def validate_google_maps_value(value, path, errors):
    if not is_nonempty_string(value):
        return
    if not valid_url(value):
        add_error(errors, path, "must be an http(s) URL")
        return
    if is_google_maps_like_url(value) and not is_direct_google_maps_profile_url(value):
        add_error(errors, path, "must be the clinic's Google Maps profile link, not a search, route or street-address link")


def validate_location_rows(clinic, path, errors):
    locations = clinic.get("locations")
    if not isinstance(locations, list):
        return
    for location_index, location in enumerate(locations):
        location_path = f"{path}.locations[{location_index}]"
        if isinstance(location, str):
            parts = [part.strip() for part in location.split("|")]
            if len(parts) >= 4:
                validate_google_maps_value(parts[3], f"{location_path}.maps_url", errors)
            if len(parts) >= 5 and parts[4]:
                if not valid_url(parts[4]):
                    add_error(errors, f"{location_path}.google_reviews_url", "must be an http(s) URL")
            continue
        if not isinstance(location, dict):
            continue
        for key in ("maps_url", "google_maps_url", "map_url"):
            if key in location:
                validate_google_maps_value(location.get(key), f"{location_path}.{key}", errors)
        for key in ("google_reviews_url", "reviews_url", "valoraciones_url"):
            if is_nonempty_string(location.get(key)) and not valid_url(location.get(key)):
                add_error(errors, f"{location_path}.{key}", "must be an http(s) URL")


def validate_clinics(errors, warnings):
    clinics = load_json(CLINICS_FILE, errors)
    if clinics is None:
        return []
    if not isinstance(clinics, list):
        add_error(errors, "data/clinics.json", "root must be a list")
        return []

    seen_slugs = set()
    seen_webs = {}

    for index, clinic in enumerate(clinics):
        path = f"data/clinics.json[{index}]"
        if not isinstance(clinic, dict):
            add_error(errors, path, "clinic must be an object")
            continue

        slug = clinic.get("slug")
        if not is_nonempty_string(slug):
            add_error(errors, path, "missing slug")
        elif not SLUG_RE.match(slug):
            add_error(errors, f"{path}.slug", "must use lowercase letters, numbers and hyphens")
        elif slug in seen_slugs:
            add_error(errors, f"{path}.slug", f"duplicate slug {slug!r}")
        else:
            seen_slugs.add(slug)

        for key in REQUIRED_STRINGS:
            if not is_nonempty_string(clinic.get(key)):
                add_error(errors, f"{path}.{key}", "required non-empty string")

        if is_nonempty_string(clinic.get("web")):
            web = clinic["web"].rstrip("/")
            if not valid_url(web):
                add_error(errors, f"{path}.web", "must be an http(s) URL")
            elif web in seen_webs:
                warnings.append(f"{path}.web: same website as {seen_webs[web]}")
            else:
                seen_webs[web] = slug or path

        status = clinic.get("status")
        if status not in ALLOWED_STATUS:
            add_error(errors, f"{path}.status", f"must be one of {sorted(ALLOWED_STATUS)}")

        for key in REQUIRED_LISTS:
            values = clinic.get(key)
            if not isinstance(values, list) or not values:
                add_error(errors, f"{path}.{key}", "required non-empty list")
                continue
            bad = [value for value in values if not is_nonempty_string(value)]
            if bad:
                add_error(errors, f"{path}.{key}", "all values must be non-empty strings")

        for key in OPTIONAL_LISTS:
            if key not in clinic:
                continue
            values = clinic[key]
            if not isinstance(values, list):
                add_error(errors, f"{path}.{key}", "must be a list")
                continue
            bad = [value for value in values if not is_nonempty_string(value)]
            if bad:
                add_error(errors, f"{path}.{key}", "all values must be non-empty strings")

        for key in OPTIONAL_STRINGS:
            if key in clinic and not isinstance(clinic[key], str):
                add_error(errors, f"{path}.{key}", "must be a string when present")

        for key in ("maps_url", "google_maps_url", "map_url"):
            if key in clinic:
                validate_google_maps_value(clinic.get(key), f"{path}.{key}", errors)

        for key in ("google_reviews_url", "reviews_url"):
            if is_nonempty_string(clinic.get(key)) and not valid_url(clinic.get(key)):
                add_error(errors, f"{path}.{key}", "must be an http(s) URL")

        validate_location_rows(clinic, path, errors)

        if is_nonempty_string(clinic.get("summary")) and len(clinic["summary"]) < 80:
            warnings.append(f"{path}.summary: short summary")

    return clinics


def validate_logos(clinics, errors, warnings):
    if not LOGOS_FILE.exists():
        warnings.append("data/logos.json: file missing")
        return
    logos = load_json(LOGOS_FILE, errors)
    if not isinstance(logos, dict):
        add_error(errors, "data/logos.json", "root must be an object")
        return

    clinic_slugs = {clinic.get("slug") for clinic in clinics if isinstance(clinic, dict)}
    for slug, info in logos.items():
        path = f"data/logos.json.{slug}"
        if slug not in clinic_slugs:
            warnings.append(f"{path}: logo entry has no matching clinic")
        if not isinstance(info, dict):
            add_error(errors, path, "logo entry must be an object")
            continue
        if "aprobado" not in info or not isinstance(info["aprobado"], bool):
            add_error(errors, f"{path}.aprobado", "must be boolean")
        if info.get("aprobado") and not valid_url(info.get("url")):
            add_error(errors, f"{path}.url", "approved logo needs an http(s) URL")

    missing = sorted(slug for slug in clinic_slugs if slug and slug not in logos)
    if missing:
        warnings.append("data/logos.json: missing logo entries for " + ", ".join(missing))


def parse_post_header(raw):
    header, separator, _body = raw.partition("\n\n")
    if not separator:
        return {}
    meta = {}
    for line in header.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    return meta


def validate_posts(errors, warnings):
    if not POSTS_DIR.exists():
        warnings.append("data/posts: directory missing")
        return
    for path in sorted(POSTS_DIR.glob("*.md")):
        rel = str(path.relative_to(ROOT))
        raw = path.read_text(encoding="utf-8")
        meta = parse_post_header(raw)
        for key in ("title", "date", "desc"):
            if not is_nonempty_string(meta.get(key)):
                add_error(errors, f"{rel}.{key}", "required front matter value")
        if meta.get("date") and not DATE_RE.match(meta["date"]):
            add_error(errors, f"{rel}.date", "must use YYYY-MM-DD")


def main():
    errors = []
    warnings = []
    clinics = validate_clinics(errors, warnings)
    validate_logos(clinics, errors, warnings)
    validate_posts(errors, warnings)

    if errors:
        print("Data validation failed:")
        for error in errors:
            print(f"- {error}")
        if warnings:
            print("\nWarnings:")
            for warning in warnings:
                print(f"- {warning}")
        return 1

    published = sum(1 for clinic in clinics if clinic.get("status") == "publicada")
    preliminary = sum(1 for clinic in clinics if clinic.get("status") == "preliminar")
    print(f"OK data: {len(clinics)} clinics ({published} published, {preliminary} preliminary)")
    for warning in warnings:
        print(f"WARN: {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
