#!/usr/bin/env python3
"""Compare the public Supabase clinic feed with the currently published site."""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from typing import Any


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_BASE_URL = "https://www.vitalarga.com"
DEFAULT_SUPABASE_URL = "https://twxhcmvzbpnrneywdece.supabase.co"
DEFAULT_SUPABASE_PUBLISHABLE_KEY = "sb_publishable_IHIMbYQacziyL1GcU6Mdtw_7AQdaCWg"
MAX_RESPONSE_BYTES = 2_000_000


def load_env_file() -> dict[str, str]:
    values: dict[str, str] = {}
    path = os.path.join(ROOT, ".env")
    if not os.path.exists(path):
        return values
    with open(path, encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip("\"'")
    return values


def env_value(key: str, local_env: dict[str, str], default: str = "") -> str:
    return os.environ.get(key) or local_env.get(key) or default


def clean_base_url(value: str) -> str:
    base = str(value or DEFAULT_BASE_URL).strip().rstrip("/")
    if not base.startswith(("https://", "http://")):
        raise SystemExit("--base-url must start with http:// or https://")
    return base


def fetch_text(url: str, timeout: int) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "VitalargaFreshnessCheck/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status = int(getattr(response, "status", response.getcode()))
        body = response.read(MAX_RESPONSE_BYTES)
    return status, body.decode("utf-8", errors="replace")


def load_public_clinics(timeout: int, local_env: dict[str, str]) -> list[dict[str, Any]]:
    url = env_value("SUPABASE_URL", local_env, DEFAULT_SUPABASE_URL).rstrip("/")
    key = env_value("SUPABASE_PUBLISHABLE_KEY", local_env, DEFAULT_SUPABASE_PUBLISHABLE_KEY)
    if not url or not key:
        raise RuntimeError("missing Supabase public config")
    request = urllib.request.Request(
        url + "/rest/v1/rpc/public_clinics_for_site",
        data=b"{}",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "VitalargaFreshnessCheck/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        clinics = json.loads(response.read().decode("utf-8"))
    if not isinstance(clinics, list):
        raise RuntimeError("Supabase clinic feed did not return a list")
    return [clinic for clinic in clinics if isinstance(clinic, dict)]


def visible_values(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value or "").strip()]


def split_text_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return visible_values(value)
    text = str(value or "").strip()
    if not text:
        return []
    for sep in ("\n", ";"):
        text = text.replace(sep, ",")
    return [part.strip() for part in text.split(",") if part.strip()]


def normalize_digits(value: str) -> str:
    return re.sub(r"\D+", "", value or "")


def compact_value(value: str, limit: int = 96) -> str:
    clean = re.sub(r"\s+", " ", str(value or "").strip())
    return clean if len(clean) <= limit else clean[: limit - 1].rstrip() + "…"


def text_needles(value: str) -> list[str]:
    clean = re.sub(r"\s+", " ", str(value or "").strip())
    if not clean:
        return []
    return [clean, html.escape(clean, quote=True)]


def marker(field: str, value: str, mode: str = "text") -> dict[str, str]:
    return {"field": field, "value": compact_value(value), "mode": mode}


def clinic_markers(clinic: dict[str, Any]) -> list[dict[str, str]]:
    markers: list[dict[str, str]] = []
    for field in ("email", "instagram"):
        value = str(clinic.get(field) or "").strip()
        if value:
            markers.append(marker(field, value))

    phone = str(clinic.get("telefono") or clinic.get("phone") or clinic.get("telephone") or "").strip()
    if normalize_digits(phone):
        markers.append(marker("telefono", phone, "digits"))

    for field in ("services", "specialties", "unidades", "profesionales", "locations"):
        values = clinic.get(field) if isinstance(clinic.get(field), list) else []
        for value in values:
            if isinstance(value, dict):
                for nested_key in ("name", "label", "city", "address"):
                    nested_value = str(value.get(nested_key) or "").strip()
                    if nested_value:
                        markers.append(marker(f"{field}.{nested_key}", nested_value))
            else:
                clean_value = str(value or "").strip()
                if clean_value:
                    markers.append(marker(field, clean_value))

    for value in split_text_list(clinic.get("tech")):
        markers.append(marker("tech", value))

    for field in (
        "years_in_practice",
        "specialists_count",
        "team_credentialing_visible",
        "public_pricing",
    ):
        value = str(clinic.get(field) or "").strip()
        if value:
            markers.append(marker(field, value))

    return markers


def marker_present(page_html: str, item: dict[str, str]) -> bool:
    if item.get("mode") == "digits":
        digits = normalize_digits(item.get("value", ""))
        page_digits = normalize_digits(page_html)
        if digits and digits in page_digits:
            return True
        if digits.startswith("34") and len(digits) > 9:
            return digits[2:] in page_digits
        return False
    return any(needle and needle in page_html for needle in text_needles(item.get("value", "")))


def check_clinic(clinic: dict[str, Any], page_html: str, missing_limit: int) -> dict[str, Any]:
    markers = clinic_markers(clinic)
    missing = [item for item in markers if not marker_present(page_html, item)]
    return {
        "slug": clinic.get("slug"),
        "name": clinic.get("name"),
        "status": clinic.get("status"),
        "expected_markers": len(markers),
        "missing_markers": len(missing),
        "missing_examples": missing[:missing_limit],
        "fresh": not missing,
    }


def clinic_matches_query(clinic: dict[str, Any], query: str) -> bool:
    clean = str(query or "").strip().lower()
    if not clean:
        return True
    values = [
        clinic.get("slug"),
        clinic.get("name"),
        clinic.get("display_name"),
        clinic.get("canonical_name"),
        clinic.get("city"),
        clinic.get("country"),
    ]
    haystack = " ".join(str(value or "").lower() for value in values)
    compact_query = compact_lookup_key(clean)
    compact_haystack = compact_lookup_key(haystack)
    return clean in haystack or bool(compact_query and compact_query in compact_haystack)


def compact_lookup_key(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return "".join(char for char in ascii_value if char.isalnum())


def run_freshness_check(
    base_url: str,
    timeout: int,
    slug: str = "",
    missing_limit: int = 8,
    clinic_query: str = "",
) -> dict[str, Any]:
    local_env = load_env_file()
    base = clean_base_url(base_url)
    clinics = load_public_clinics(timeout, local_env)
    if slug:
        clinics = [clinic for clinic in clinics if str(clinic.get("slug") or "") == slug]
    if clinic_query:
        clinics = [clinic for clinic in clinics if clinic_matches_query(clinic, clinic_query)]
    results = []
    for clinic in clinics:
        clinic_slug = str(clinic.get("slug") or "").strip()
        if not clinic_slug:
            continue
        url = f"{base}/clinica/{clinic_slug}/"
        try:
            status, body = fetch_text(url, timeout)
            result = check_clinic(clinic, body, missing_limit)
            result.update({"url": url, "http_status": status, "error": ""})
        except (OSError, urllib.error.URLError, TimeoutError) as exc:
            result = {
                "slug": clinic_slug,
                "name": clinic.get("name"),
                "status": clinic.get("status"),
                "url": url,
                "http_status": None,
                "expected_markers": 0,
                "missing_markers": 0,
                "missing_examples": [],
                "fresh": False,
                "error": str(exc),
            }
        results.append(result)

    stale = [item for item in results if not item.get("fresh")]
    return {
        "base_url": base,
        "clinic_count": len(results),
        "stale_count": len(stale),
        "ok": not stale,
        "writes_data": False,
        "clinic_query": clinic_query,
        "checks": results,
    }


def format_report(report: dict[str, Any]) -> str:
    lines = [
        "# Vitalarga public-site freshness",
        "",
        f"Base: {report.get('base_url')}",
    ]
    if report.get("clinic_query"):
        lines.append(f"Consulta: {report.get('clinic_query')}")
    lines.extend([
        f"Estado: {'OK' if report.get('ok') else 'Atención'}",
        "- Writes data: no",
        f"- Clínicas revisadas: {report.get('clinic_count', 0)}",
        f"- Con desfase: {report.get('stale_count', 0)}",
        "",
        "## Desfases",
    ])
    stale = [item for item in report.get("checks") or [] if not item.get("fresh")]
    if not stale:
        lines.append("- Ninguno detectado.")
    for item in stale:
        detail = f"{item.get('missing_markers', 0)} campos no aparecen"
        if item.get("error"):
            detail = "error: " + str(item["error"])[:160]
        lines.append(f"- {item.get('name')}: {detail} · {item.get('url')}")
        if item.get("missing_markers") and not item.get("error"):
            lines.append("  - Motivo probable: Supabase tiene datos que la web publicada todavía no ha incorporado; falta regenerar la web pública.")
        for missing in item.get("missing_examples") or []:
            lines.append(f"  - {missing.get('field')}: {missing.get('value')}")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=int, default=12)
    parser.add_argument("--slug", default="", help="Check one clinic slug only.")
    parser.add_argument("--clinic", default="", help="Check clinics matching a normal name, city or slug.")
    parser.add_argument("--missing-limit", type=int, default=8)
    parser.add_argument("--json", action="store_true", help="Print raw JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.timeout < 3 or args.timeout > 60:
        raise SystemExit("--timeout must be between 3 and 60 seconds.")
    if args.missing_limit < 1 or args.missing_limit > 30:
        raise SystemExit("--missing-limit must be between 1 and 30.")
    report = run_freshness_check(args.base_url, args.timeout, args.slug.strip(), args.missing_limit, args.clinic.strip())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_report(report), end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
