#!/usr/bin/env python3
"""Shadow extractor for a clinic profile source.

This is the first non-AI extractor. It turns one page into structured candidate
facts and field claims, but it never publishes. Later an LLM extractor can share
the same output shape.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from capture_source_snapshot import (
    FetchResult,
    fetch_url,
    load_from_html_file,
    normalize_space,
    safe_host,
    snapshot_from_fetch,
)
from diuvita_rules import decide_many


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "data" / "extractions"
EXTRACTION_EXCERPT_CHARS = 5000

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d\s()./-]{7,}\d)(?!\w)")
INSTAGRAM_URL_RE = re.compile(r"https?://(?:www\.)?instagram\.com/([a-z0-9._]{2,30})(?:/|\b)", re.I)
INSTAGRAM_HANDLE_RE = re.compile(r"(?<![\w.+-])@([a-z0-9._]{2,30})(?![\w.-])", re.I)
NAME_WORD = r"[A-ZÁÉÍÓÚÜÑ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ'-]{2,}"
PROFESSIONAL_RE = re.compile(
    rf"\b(?:Dr\.?|Dra\.?|Doctor|Doctora)\s+{NAME_WORD}(?:\s+{NAME_WORD}){{1,3}}"
)

KEYWORD_CATALOG = {
    "services.list": {
        "Longevidad": ["longevidad", "longevity"],
        "Medicina preventiva": ["medicina preventiva", "preventive medicine"],
        "Medicina de precisión": ["medicina de precisión", "precision medicine"],
        "Chequeo médico avanzado": ["chequeo", "check-up", "checkup", "health assessment"],
        "Nutrición": ["nutrición", "nutrition"],
        "Salud hormonal": ["hormonal", "hormone"],
        "Medicina del sueño": ["sueño", "sleep medicine"],
        "Medicina deportiva": ["medicina deportiva", "sports medicine"],
        "Microbiota": ["microbiota", "gut health"],
        "Sueroterapia IV": ["sueroterapia", "iv therapy", "intravenous"],
    },
    "technologies.list": {
        "VO2 max": ["vo2", "vo2max", "vo2 max"],
        "DEXA": ["dexa"],
        "Resonancia magnética": ["resonancia", "magnetic resonance", "mri"],
        "AngioTAC": ["angiotac", "angio-tc", "angio tac"],
        "Test genético": ["test genético", "genetic test", "genomics"],
        "Test epigenético": ["epigenético", "epigenetic"],
        "Biomarcadores": ["biomarcadores", "biomarkers"],
        "Monitorización continua de glucosa": ["monitorización continua de glucosa", "continuous glucose"],
        "Hipoxia intermitente": ["hipoxia", "ihht"],
        "Plasmaféresis": ["plasmaféresis", "plasmapheresis"],
        "NAD+": ["nad+"],
        "Ozonoterapia": ["ozonoterapia", "ozone therapy"],
    },
    "units.list": {
        "Unidad de Longevidad": ["unidad de longevidad", "longevity unit"],
        "Unidad de Medicina Preventiva": ["unidad de medicina preventiva", "preventive medicine unit"],
        "Unidad del Dolor": ["unidad del dolor", "unidad de dolor", "pain unit"],
        "Unidad del Sueño": ["unidad del sueño", "unidad de sueño", "sleep unit"],
        "Unidad de Salud Hormonal": ["unidad hormonal", "unidad de salud hormonal", "hormone unit"],
    },
    "specialties.list": {
        "Longevidad": ["longevidad", "longevity"],
        "Medicina preventiva": ["medicina preventiva", "preventive medicine"],
        "Medicina integrativa": ["medicina integrativa", "integrative medicine"],
        "Endocrinología": ["endocrinología", "endocrinology"],
        "Cardiología": ["cardiología", "cardiology"],
        "Neurología": ["neurología", "neuro"],
        "Nutrición": ["nutrición", "nutrition"],
        "Ginecología": ["ginecología", "gynecology", "gynaecology"],
        "Medicina estética regenerativa": ["estética regenerativa", "regenerative aesthetic"],
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def unique(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        clean = normalize_space(item)
        key = clean.lower()
        if clean and key not in seen:
            seen.add(key)
            result.append(clean)
    return result


def clean_phone(raw: str) -> str:
    return normalize_space(raw).strip(".,;:")


def extract_contacts(text: str) -> dict[str, list[str]]:
    emails = unique(EMAIL_RE.findall(text))
    phones = unique([clean_phone(match.group(0)) for match in PHONE_RE.finditer(text)])
    instagram = unique(
        ["@" + match.group(1).strip("/").lower() for match in INSTAGRAM_URL_RE.finditer(text)]
        + ["@" + match.group(1).strip("/").lower() for match in INSTAGRAM_HANDLE_RE.finditer(text)]
    )
    return {
        "emails": emails[:5],
        "phones": phones[:5],
        "instagram": instagram[:5],
    }


def extract_professionals(text: str) -> list[str]:
    return unique([match.group(0).strip(".,;:") for match in PROFESSIONAL_RE.finditer(text)])


def detect_keywords(text: str) -> dict[str, list[str]]:
    lower = text.lower()
    detected: dict[str, list[str]] = {}
    for field_path, labels in KEYWORD_CATALOG.items():
        values = []
        for label, needles in labels.items():
            if any(needle.lower() in lower for needle in needles):
                values.append(label)
        detected[field_path] = values
    return detected


def guess_name(snapshot: dict[str, Any]) -> str:
    title = normalize_space(str(snapshot.get("source_title") or ""))
    if not title:
        return ""
    for separator in (" | ", " - ", " – ", " — "):
        if separator in title:
            return normalize_space(title.split(separator, 1)[0])
    return title[:90]


def claim(field_path: str, value: Any, confidence: float, source_url: str) -> dict[str, Any]:
    return {
        "field_path": field_path,
        "value": value,
        "confidence": confidence,
        "source_count": 1,
        "source_url": source_url,
        "verifier_verdict": "unknown",
        "agent_name": "diuvita-shadow-extractor",
        "agent_version": "2026-08-30",
    }


def build_claims(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    source_url = str(snapshot.get("final_url") or snapshot.get("source_url") or "")
    text = normalize_space(str(snapshot.get("text_excerpt") or ""))
    contacts = extract_contacts(text)
    professionals = extract_professionals(text)
    keywords = detect_keywords(text)
    claims: list[dict[str, Any]] = []

    name = guess_name(snapshot)
    if name:
        claims.append(claim("identity.canonical_name", name, 0.55, source_url))
    if source_url:
        parsed = urlparse(source_url)
        claims.append(claim("contact.website", f"{parsed.scheme}://{parsed.netloc}", 0.86, source_url))
    if contacts["emails"]:
        claims.append(claim("contact.email", contacts["emails"][0], 0.88, source_url))
    if contacts["phones"]:
        claims.append(claim("contact.phone", contacts["phones"][0], 0.78, source_url))
    if contacts["instagram"]:
        claims.append(claim("contact.instagram", contacts["instagram"][0], 0.80, source_url))
    if professionals:
        claims.append(claim("professionals.published", professionals[:8], 0.64, source_url))
    for field_path, values in keywords.items():
        if values:
            claims.append(claim(field_path, values, 0.70, source_url))
    return claims


def build_profile(snapshot: dict[str, Any]) -> dict[str, Any]:
    text = normalize_space(str(snapshot.get("text_excerpt") or ""))
    contacts = extract_contacts(text)
    professionals = extract_professionals(text)
    keywords = detect_keywords(text)
    profile = {
        "name": guess_name(snapshot) or None,
        "website": claim_website(str(snapshot.get("final_url") or snapshot.get("source_url") or "")),
        "emails": contacts["emails"],
        "phones": contacts["phones"],
        "instagram": contacts["instagram"],
        "services": keywords.get("services.list", []),
        "specialties": keywords.get("specialties.list", []),
        "units": keywords.get("units.list", []),
        "professionals": professionals[:8],
        "technologies": keywords.get("technologies.list", []),
    }
    return {key: value for key, value in profile.items() if value}


def claim_website(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return None


def extract_from_fetch(result: FetchResult) -> dict[str, Any]:
    snapshot = snapshot_from_fetch(result, excerpt_chars=EXTRACTION_EXCERPT_CHARS)
    claims = build_claims(snapshot)
    return {
        "workflow": "EXTRACT_CLINIC_PROFILE",
        "mode": "shadow",
        "extracted_at": now_iso(),
        "source": snapshot,
        "candidate_profile": build_profile(snapshot),
        "field_claims": claims,
        "rule_decisions": decide_many(claims),
    }


def output_path(extraction: dict[str, Any], base_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    source = extraction.get("source") or {}
    retrieved = str(extraction.get("extracted_at") or now_iso())
    year = retrieved[:4]
    month = retrieved[5:7]
    host = safe_host(str(source.get("final_url") or source.get("source_url") or "unknown"))
    digest = str(source.get("content_sha256") or "nohash")[:16]
    return base_dir / year / month / host / f"{digest}.json"


def write_extraction(extraction: dict[str, Any], base_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    path = output_path(extraction, base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(extraction, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="Clinic source URL.")
    parser.add_argument("--html-file", type=Path, help="Use local HTML instead of fetching.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--write", action="store_true", help="Write extraction JSON under data/extractions.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.html_file:
        result = load_from_html_file(args.html_file, args.url)
    else:
        result = fetch_url(args.url)
    extraction = extract_from_fetch(result)
    if args.write:
        path = write_extraction(extraction, args.output_dir)
        print(os.path.relpath(path, ROOT))
    else:
        print(json.dumps(extraction, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
