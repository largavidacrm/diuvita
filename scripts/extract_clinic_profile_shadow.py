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
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from capture_source_snapshot import (
    FetchResult,
    decode_body,
    fetch_url,
    load_from_html_file,
    normalize_space,
    parse_html,
    safe_host,
    snapshot_from_fetch,
)
from vitalarga_rules import decide_many


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "data" / "extractions"
EXTRACTION_EXCERPT_CHARS = 5000
MAX_PROFESSIONALS = 32
MAX_LOCATIONS = 8
SUMMARY_MIN_CHARS = 90
SUMMARY_MAX_CHARS = 280

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d\s()./-]{7,}\d)(?!\w)")
INSTAGRAM_URL_RE = re.compile(r"https?://(?:www\.)?instagram\.com/([a-z0-9._]{2,30})(?:/|\b)", re.I)
INSTAGRAM_HANDLE_RE = re.compile(r"(?<![\w.+-])@([a-z0-9._]{2,30})(?![\w.-])", re.I)
YEARS_IN_PRACTICE_RE = re.compile(
    r"\b(?P<prefix>m[aá]s\s+de|over|more\s+than)?\s*(?P<years>\d{2,3})\s+"
    r"años\s+(?:de\s+)?(?P<context>experiencia|trayectoria|ejercicio|actividad|pr[aá]ctica)\b",
    re.I,
)
DECADE_IN_PRACTICE_RE = re.compile(
    r"\b(?:(?:experiencia|trayectoria|ejercicio|actividad|pr[aá]ctica)[^.]{0,50}?)?"
    r"(?P<prefix>m[aá]s\s+de|over|more\s+than)?\s*"
    r"(?P<decades>un|una|dos|tres|cuatro|cinco|\d{1,2})\s+d[eé]cada[s]?\b"
    r"(?:[^.]{0,50}(?:experiencia|trayectoria|ejercicio|actividad|pr[aá]ctica))?",
    re.I,
)
SPECIALISTS_COUNT_RE = re.compile(
    r"\b(?P<prefix>m[aá]s\s+de|over|more\s+than|equipo\s+de|cuenta\s+con)?\s*"
    r"(?P<count>\d{1,3})\s+(?:especialistas|profesionales\s+m[eé]dicos|profesionales|m[eé]dicos)\b",
    re.I,
)
TEAM_CREDENTIALING_RE = re.compile(
    r"\b(?:n[ºo]\s*colegiad[oa]|n[uú]mero\s+de\s+colegiad[oa]|"
    r"colegiad[oa]\s*(?:n[ºo]|n[uú]mero)|col\.)\b",
    re.I,
)
PUBLIC_PRICING_RE = re.compile(
    r"(?:precio|tarifa|consulta|programa|bono)[^.]{0,90}(?:€|eur|euros)|"
    r"(?:€|eur|euros)[^.]{0,90}(?:precio|tarifa|consulta|programa|bono)",
    re.I,
)
SUMMARY_NOISE_RE = re.compile(
    r"\b(?:"
    r"acceptance|aceptaci[oó]n|additional information|apellido|blog articles|"
    r"cookie policy|contact(?:ar)?|correo electr[oó]nico|faq|journal|legal notice|"
    r"newsletter|pol[ií]tica de privacidad|privacy policy|reciba informaci[oó]n|"
    r"receive updated information|recipients|redes sociales|responsable|rights|"
    r"social networks|subscribe|suscr[ií]bete|suscribirse|your email"
    r")\b",
    re.I,
)
SUMMARY_SIGNAL_TERMS = (
    "bienestar",
    "biomarcadores",
    "clinic",
    "clínica",
    "clinica",
    "diagnóstico",
    "diagnostico",
    "health",
    "longevidad",
    "longevity",
    "medicine",
    "medicina",
    "personalised",
    "personalized",
    "personalizados",
    "preventive",
    "preventiva",
    "programas",
    "programmes",
    "salud",
    "technology-led",
    "tratamientos",
    "wellbeing",
)
SUMMARY_SPANISH_TERMS = (
    "clínica",
    "clinica",
    "diagnóstico",
    "diagnostico",
    "medicina",
    "ofrece",
    "personalizados",
    "programas",
    "salud",
    "tratamientos",
)
LOCATION_ADDRESS_RE = re.compile(
    r"\b(?P<address>(?:C/|C\.|Calle|Carrer|Paseo|Pº|P.º|Passeig|Avenida|Av\.?|Avda\.?|"
    r"Plaza|Pza\.?|Ronda|"
    r"Carretera|Camino|Vía|Via|Gran Vía|Road|Street|Avenue)\s+"
    r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9][^|]{4,180}?"
    r"(?:\b\d{5}\b\s*,?\s*(?:Barcelona|Madrid|Valencia|Marbella|Málaga|Malaga|Sevilla|Bilbao|Alicante|"
    r"Zaragoza|Murcia|Palma|Vigo|Granada|Girona|Tarragona)|"
    r"Barcelona|Madrid|Valencia|Marbella|Málaga|Malaga|Sevilla|Bilbao|Alicante|"
    r"Zaragoza|Murcia|Palma|Vigo|Granada|Girona|Tarragona))",
    re.I,
)
ADDRESS_STOP_RE = re.compile(
    r"\b(?:tel[eé]fono|email|correo|contacto|horario|ver mapa|google maps|"
    r"c[oó]mo llegar|como llegar|reservar|pedir cita)\b",
    re.I,
)
CITY_HINTS = (
    "Barcelona",
    "Madrid",
    "Valencia",
    "Marbella",
    "Málaga",
    "Malaga",
    "Sevilla",
    "Bilbao",
    "Alicante",
    "Zaragoza",
    "Murcia",
    "Palma",
    "Vigo",
    "Granada",
    "Girona",
    "Tarragona",
)
NAME_WORD = r"[A-ZÁÉÍÓÚÜÑ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ'-]{2,}"
TITLE_PREFIX = r"(?:Dr\.?|Dra\.?|Doctor|Doctora|Lic\.?|Licenciado|Licenciada|D\.O\.?)"
PROFESSIONAL_RE = re.compile(
    rf"\b(?P<title>{TITLE_PREFIX})\s+(?P<name>{NAME_WORD}(?:\s+{NAME_WORD}){{0,5}})"
)
TITLE_SCAN_RE = re.compile(rf"\b(?P<title>{TITLE_PREFIX})\s+")
TITLE_SEGMENT_STOP_RE = re.compile(
    r"\b(?:"
    r"a\s+graduate|an\s+expert|a\s+specialist|is|are|was|were|has|have|having|"
    r"cares|boasting|graduate|specialist|practitioner|renowned|laureate|"
    r"university|hospital|faculty|department|private|clinic|clinics|geneva|switzerland|london-based"
    r")\b",
    re.I,
)
TEAM_MARKERS = (
    "equipo",
    "equipo de",
    "nuestro equipo",
    "nuestros profesionales",
    "equipo medico",
    "equipo médico",
    "equipo profesional",
    "profesionales medicos",
    "profesionales médicos",
    "staff medico",
    "staff médico",
    "cuadro medico",
    "cuadro médico",
    "our team",
    "our team of experts",
    "team of experts",
    "medical board",
    "clinicians",
    "advisory board",
)
TEAM_PAGE_MARKERS = tuple(
    marker for marker in TEAM_MARKERS if marker not in {"equipo", "equipo de"}
)
TEAM_END_MARKERS = (
    "contáctanos",
    "contactanos",
    "contacto",
    "menú legal",
    "menu legal",
    "©",
)
NAV_END_MARKERS = (
    "select page",
    "saltar al contenido",
    "skip to content",
)
ROLE_PHRASES = (
    "Cardiología",
    "Chequeos de Longevidad",
    "Coordinación médica",
    "Coordinacion medica",
    "Dermatología",
    "Dermatología Estética",
    "Dirección",
    "Dirección médica",
    "Direccion medica",
    "Director",
    "Directora",
    "Endocrinología",
    "Fisioterapia",
    "Fisioterapeuta",
    "Gerente / Nutrición",
    "Gerente/Nutrición",
    "Gerente",
    "Ginecología",
    "Nutrición",
    "Nutrición funcional",
    "Nutricionista y experta en Microbiota",
    "Nutricionista",
    "Subdirectora",
    "Subdirector",
    "Medicina Antienvejecimiento",
    "Medicina de Longevidad",
    "Medicina Estética y Longevidad",
    "Medicina Funcional",
    "Medicina General",
    "Medicina Integrativa",
    "Medicina Interna",
    "Medicina Regenerativa",
    "Odontología y Posturología",
    "Odontología",
    "Odontóloga",
    "Odontologo",
    "Odontólogo",
    "Óptica Optometrista",
    "Optica Optometrista",
    "Optometrista",
    "Podoposturóloga",
    "Podoposturologa",
    "Ginecología regenerativa y Salud integral de la mujer",
    "Neurofisiólogo clínico",
    "Oncología Integrativa",
    "Osteópata",
    "Osteopata",
    "Otorrinolaringología",
    "Otorrino",
    "Anestesia",
    "Flebología",
    "Cirugía Plástica",
    "Psicología",
    "Psicologia",
    "Atención al Paciente",
    "Atencion al paciente",
    "Auxiliar de enfermería",
    "Auxiliar de enfermeria",
    "Cirujana vascular",
    "Cirujano vascular",
    "Coordinadora de estética",
    "Coordinadora de estetica",
    "Coordinador de estética",
    "Coordinador de estetica",
    "Coordinadora del área de atencion al paciente",
    "Coordinadora del área de atención al paciente",
    "Coordinador del área de atencion al paciente",
    "Coordinador del área de atención al paciente",
    "Dermatóloga pediátrica",
    "Dermatologa pediatrica",
    "Dermatólogo pediátrico",
    "Dermatologo pediatrico",
    "Dermatóloga y Médico Estético",
    "Dermatologa y Medico Estetico",
    "Dermatólogo y Médico Estético",
    "Dermatologo y Medico Estetico",
    "Dermatóloga",
    "Dermatologa",
    "Dermatólogo",
    "Dermatologo",
    "Enfermera",
    "Enfermero",
    "Gerente administrativo",
    "Médico Estético",
    "Medico Estetico",
    "Radióloga y Médico Estético",
    "Radiologa y Medico Estetico",
    "Radiólogo y Médico Estético",
    "Radiologo y Medico Estetico",
    "Radióloga",
    "Radiologa",
    "Radiólogo",
    "Radiologo",
    "Responsable de Ensayos clínicos",
    "Responsable de Ensayos clinicos",
    "Traumatólogo",
    "Traumatologo",
    "Técnico Auxiliar",
    "Responsable RRSS",
    "Staff",
    "Higienista",
    "Auxiliar",
    "Recepción",
    "Recepcion",
)
ROLE_START_WORDS = {
    "Administración",
    "Anestesia",
    "Analítica",
    "Analitica",
    "Atención",
    "Atencion",
    "Cardiología",
    "Cardiologia",
    "Cardióloga",
    "Cardiologa",
    "Cardiólogo",
    "Cardiologo",
    "CCOEC",
    "CFC",
    "CNOO",
    "COEC",
    "COMB",
    "COMM",
    "Chequeos",
    "Cirujana",
    "Cirujano",
    "Cirugía",
    "Consulta",
    "Cosmética",
    "Cosmetica",
    "Clínico",
    "Clinico",
    "Director",
    "Directora",
    "Dirección",
    "Dermatología",
    "Dermatologia",
    "Dermatóloga",
    "Dermatologa",
    "Dermatólogo",
    "Dermatologo",
    "Endocrinología",
    "Endocrinologia",
    "Endocrinóloga",
    "Endocrinologa",
    "Endocrinólogo",
    "Endocrinologo",
    "Enfermera",
    "Enfermero",
    "Especialista",
    "Estética",
    "Estetica",
    "Experta",
    "Experto",
    "Fertilidad",
    "Fisioterapia",
    "Fisioterapeuta",
    "Flebología",
    "Flebologia",
    "Frotis",
    "General",
    "Gerencia",
    "Gerente",
    "Coordinadora",
    "Coordinador",
    "Ginecológica",
    "Ginecologica",
    "Ginecología",
    "Ginecologia",
    "Ginecóloga",
    "Ginecologa",
    "Ginecólogo",
    "Ginecologo",
    "Higienista",
    "Interna",
    "Longevidad",
    "Microbiota",
    "Médica",
    "Médicina",
    "Médico",
    "Medicina",
    "Medico",
    "Integrativa",
    "Mujer",
    "Neurofisiólogo",
    "Neurofisiologo",
    "Nutrición",
    "Nutricion",
    "Nutricionista",
    "Radióloga",
    "Radiologa",
    "Radiólogo",
    "Radiologo",
    "Odontología",
    "Odontologia",
    "Odontóloga",
    "Odontologa",
    "Odontólogo",
    "Odontologo",
    "Oncológica",
    "Oncologica",
    "Oncología",
    "Oncologia",
    "Ortomolecular",
    "Osteópata",
    "Osteopata",
    "Otorrino",
    "Otorrinolaringología",
    "Otorrinolaringologia",
    "Optica",
    "Óptica",
    "Optometrista",
    "Paciente",
    "Pediátrico",
    "Pediatrico",
    "Podoposturóloga",
    "Podoposturologa",
    "PNIE",
    "Psicología",
    "Psicologia",
    "Recepción",
    "Recepcion",
    "Responsable",
    "Salud",
    "Sanguíneo",
    "Sanguineo",
    "Sesion",
    "Sesión",
    "Blog",
    "Beneficios",
    "Franquicias",
    "Historia",
    "Hombre",
    "Método",
    "Metodo",
    "Mujer",
    "Pilares",
    "Suplementos",
    "Testimonios",
    "Tratamiento",
    "Tratamientos",
    "Auxiliar",
    "Subdirector",
    "Subdirectora",
    "Técnico",
    "Traumatólogo",
    "Traumatologo",
    "Unidad",
    "Unidades",
}
TITLE_WORDS = {"Dr", "Dra", "Doctor", "Doctora", "Lic", "Licenciado", "Licenciada", "D", "DO"}
CLINIC_NAME_TERMS = {
    "age",
    "center",
    "centre",
    "clinic",
    "clínica",
    "clinica",
    "health",
    "healthspan",
    "hospital",
    "institute",
    "instituto",
    "longevity",
    "longevidad",
    "medical",
    "medicina",
    "wellness",
}
TITLE_NOISE_TERMS = {
    "adaptarse",
    "bienvenido",
    "contacto",
    "equipo",
    "experts",
    "expertos",
    "home",
    "inicio",
    "nace",
    "pasión",
    "quienes",
    "servicios",
    "somos",
    "team",
}
DECADE_WORDS = {
    "un": 1,
    "una": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
}


def role_pattern(phrase: str) -> str:
    escaped = re.escape(phrase)
    escaped = escaped.replace(r"\ ", r"\s+")
    return escaped.replace("/", r"\s*/\s*")


ROLE_RE_FRAGMENT = "|".join(role_pattern(phrase) for phrase in sorted(ROLE_PHRASES, key=len, reverse=True))
MEMBER_ARCHIVE_NAME_RE = re.compile(
    rf"\b(?P<label>{NAME_WORD})(?:\s+[A-ZÁÉÍÓÚÜÑ]\b)?\s+"
    rf"(?P=label)\s+"
    rf"(?P<rest>[A-Za-zÁÉÍÓÚÜÑáéíóúüñ'-]{{2,}}(?:\s+[A-Za-zÁÉÍÓÚÜÑáéíóúüñ'-]{{2,}}){{0,3}})"
    rf"(?=\s+(?i:{ROLE_RE_FRAGMENT}))",
    re.I,
)
TEAM_ROLE_PAIR_RE = re.compile(
    rf"\b(?P<name>(?:{TITLE_PREFIX}\s+)?{NAME_WORD}(?:\s+{NAME_WORD}){{0,3}})\s+"
    rf"(?P<role>(?i:{ROLE_RE_FRAGMENT}))(?=\s|$)"
)
TEAM_CTA_RE = re.compile(
    rf"(?i:\b(?:agenda\s+tu\s+cita\s+con|pide\s+cita\s+con|reserva\s+cita\s+con|cita\s+con))\s+{NAME_WORD}\b"
)
TEAM_CARD_NOISE_RE = re.compile(r"\b(?:ver\s+curriculum|curriculum|siguiente)\b", re.I)
TEAM_INLINE_CONTACT_RE = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b|(?<![\w.+-])@[a-z0-9._]{2,30}(?![\w.-])",
    re.I,
)
TEAM_SECONDARY_ROLE_RE = re.compile(rf"\s*/\s*(?i:{ROLE_RE_FRAGMENT})(?=\s+{NAME_WORD}|\s*$)")

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
        key = unicodedata.normalize("NFKD", clean.lower()).encode("ascii", "ignore").decode("ascii")
        if clean and key not in seen:
            seen.add(key)
            result.append(clean)
    return result


def fold(value: str) -> str:
    return unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii").lower()


ROLE_START_KEYS = {fold(word.rstrip(".")) for word in ROLE_START_WORDS}
TITLE_WORD_KEYS = {fold(word.rstrip(".")) for word in TITLE_WORDS}


def canonical_city(value: str) -> str:
    return "Málaga" if value == "Malaga" else value


def city_from_address(address: str) -> str:
    folded = fold(address)
    for city in sorted(CITY_HINTS, key=len, reverse=True):
        if fold(city) in folded:
            return canonical_city(city)
    match = re.search(
        r"\b\d{5}\b\s+([A-ZÁÉÍÓÚÜÑ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ-]+(?:\s+[A-ZÁÉÍÓÚÜÑ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ-]+){0,2})",
        address,
    )
    return normalize_space(match.group(1)).strip(" ,.;:") if match else ""


def clean_address(raw: str) -> str:
    first_part = ADDRESS_STOP_RE.split(raw, 1)[0]
    return normalize_space(first_part).strip(" ,.;:-")


def compact_address_key(raw: str) -> str:
    return normalize_space(re.sub(r"[^a-z0-9]+", " ", fold(raw)))


def trim_repeated_trailing_city(address: str, city: str) -> str:
    if not city:
        return address
    pattern = re.compile(rf"(\b{re.escape(city)}\b)(?:[,\s]+{re.escape(city)}\b)+$", re.I)
    return normalize_space(pattern.sub(r"\1", address)).strip(" ,.;:-")


def extract_locations(text: str) -> list[dict[str, str]]:
    locations: list[dict[str, str]] = []
    seen: set[str] = set()
    for match in LOCATION_ADDRESS_RE.finditer(text):
        address = clean_address(match.group("address"))
        if len(address) < 10:
            continue
        city = city_from_address(address)
        address = trim_repeated_trailing_city(address, city)
        key = compact_address_key(address)
        if key in seen:
            continue
        if any(key.startswith(existing + " ") or existing.startswith(key + " ") for existing in seen):
            continue
        seen.add(key)
        location: dict[str, str] = {"address": address}
        if city:
            location["city"] = city
        locations.append(location)
        if len(locations) >= MAX_LOCATIONS:
            break
    return locations


def clean_phone(raw: str) -> str:
    return normalize_space(raw).strip(".,;:")


def plausible_spanish_phone(value: str) -> bool:
    digits = spanish_phone_digits(value)
    return len(digits) == 9 and digits[0] in {"6", "7", "8", "9"}


def split_phone_candidate(raw: str) -> list[str]:
    clean = clean_phone(raw)
    digits = re.sub(r"\D", "", clean)
    if not digits:
        return []
    if clean.startswith("+") and len(digits) <= 15:
        return [clean] if plausible_spanish_phone(clean) else []
    if clean.startswith("+34") and len(digits) > 11 and (len(digits) - 2) % 9 == 0:
        phones = ["+" + digits[:11]]
        phones.extend(digits[index : index + 9] for index in range(11, len(digits), 9))
        return [phone for phone in phones if plausible_spanish_phone(phone)]
    if len(digits) in {9, 11, 13}:
        return [clean] if plausible_spanish_phone(clean) else []
    if len(digits) % 9 == 0:
        return [
            phone
            for phone in (digits[index : index + 9] for index in range(0, len(digits), 9))
            if plausible_spanish_phone(phone)
        ]
    return []


def spanish_phone_digits(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if digits.startswith("0034") and len(digits) == 13:
        return digits[4:]
    if digits.startswith("34") and len(digits) == 11:
        return digits[2:]
    return digits


def spanish_phone_kind(value: str) -> str:
    digits = spanish_phone_digits(value)
    if len(digits) != 9:
        return ""
    if digits[0] in {"6", "7"}:
        return "mobile"
    if digits[0] in {"8", "9"}:
        return "fixed"
    return ""


def first_phone_by_kind(phones: list[str], kind: str, excluded: set[str] | None = None) -> str:
    excluded = excluded or set()
    for phone in phones:
        digits = spanish_phone_digits(phone)
        if digits in excluded:
            continue
        if spanish_phone_kind(phone) == kind:
            return phone
    return ""


def professional_team_window(text: str) -> str:
    lower = text.lower()
    floor = 0
    for marker in NAV_END_MARKERS:
        pos = lower.find(marker)
        if pos >= 0:
            floor = max(floor, pos + len(marker))
    starts = [
        lower.find(marker, floor)
        for marker in TEAM_MARKERS
        if lower.find(marker, floor) >= 0
    ]
    if not starts:
        return ""
    start = min(starts)
    end_candidates = [
        lower.find(marker, start + 1)
        for marker in TEAM_END_MARKERS
        if lower.find(marker, start + 1) >= 0
    ]
    end = min(end_candidates) if end_candidates else len(text)
    return text[start:end]


def extraction_contact_prefix(text: str) -> str:
    contacts = []
    contacts.extend(EMAIL_RE.findall(text))
    contacts.extend(match.group(0).strip(".,;:") for match in PHONE_RE.finditer(text))
    contacts.extend("https://www.instagram.com/" + match.group(1).strip("/") for match in INSTAGRAM_URL_RE.finditer(text))
    seen = set()
    clean = []
    for value in contacts:
        item = normalize_space(value)
        key = fold(item)
        if item and key not in seen:
            seen.add(key)
            clean.append(item)
    return " ".join(clean[:8])


def source_looks_like_team_page(source_url: str, title: str, text: str) -> bool:
    if source_url_title_looks_like_team_page(source_url, title):
        return True
    haystack = text[:6000].lower()
    return any(marker in haystack for marker in TEAM_PAGE_MARKERS)


def source_url_title_looks_like_team_page(source_url: str, title: str) -> bool:
    url_title = " ".join([source_url, title]).replace("-", " ").replace("_", " ").lower()
    return any(marker in url_title for marker in TEAM_PAGE_MARKERS)


def extraction_text_excerpt(readable_text: str, title: str, source_url: str, limit: int) -> str:
    readable_text = normalize_space(readable_text)
    if not readable_text:
        return ""
    if not source_looks_like_team_page(source_url, title, readable_text):
        return readable_text[:limit]

    prefix = extraction_contact_prefix(readable_text)
    team_window = professional_team_window(readable_text)
    if not team_window:
        return readable_text[:limit]

    start = max(0, readable_text.find(team_window) - 260)
    focused = normalize_space(" ".join([prefix, readable_text[start : start + limit]]))
    return focused[:limit]


def extraction_snapshot_from_fetch(result: FetchResult) -> dict[str, Any]:
    html_text = decode_body(result.body, result.content_type)
    title, readable_text = parse_html(html_text)
    snapshot = snapshot_from_fetch(result, excerpt_chars=EXTRACTION_EXCERPT_CHARS)
    snapshot["source_title"] = title or snapshot.get("source_title")
    snapshot["text_excerpt"] = extraction_text_excerpt(
        readable_text,
        str(snapshot.get("source_title") or ""),
        str(snapshot.get("final_url") or snapshot.get("source_url") or ""),
        EXTRACTION_EXCERPT_CHARS,
    ) or snapshot.get("text_excerpt")
    return snapshot


def name_words(raw: str) -> list[str]:
    return re.findall(NAME_WORD, raw)


def normalize_professional_title(raw: str) -> str:
    title = normalize_space(raw).rstrip(".")
    lower = title.lower()
    if lower in {"d.o", "do"}:
        return "D.O."
    if lower.startswith(("dra", "doctora")):
        return "Dra."
    if lower.startswith(("dr", "doctor")):
        return "Dr."
    if lower.startswith(("lic", "licenciado", "licenciada")):
        return "Lic."
    return title


def title_name_segment(text: str, start: int) -> str:
    segment = text[start : start + 180]
    next_title = TITLE_SCAN_RE.search(segment)
    if next_title:
        segment = segment[: next_title.start()]
    punctuation = re.search(r"[.,;:|¿?¡!]", segment)
    if punctuation:
        segment = segment[: punctuation.start()]
    bio_stop = TITLE_SEGMENT_STOP_RE.search(segment)
    if bio_stop:
        segment = segment[: bio_stop.start()]
    return segment


def clean_titled_name(title_raw: str, name_raw: str) -> str:
    title = normalize_professional_title(title_raw)
    words = []
    for word in name_words(name_raw):
        clean_key = fold(word.rstrip("."))
        if clean_key in ROLE_START_KEYS or clean_key in TITLE_WORD_KEYS:
            break
        words.append(word)
        if len(words) >= 6:
            break
    if len(words) < 2:
        return ""
    return f"{title} {' '.join(words)}"


def clean_titled_professional(match: re.Match[str]) -> str:
    return clean_titled_name(match.group("title"), match.group("name"))


def strip_team_ctas(text: str) -> str:
    clean = TEAM_CTA_RE.sub(" ", text)
    clean = TEAM_CARD_NOISE_RE.sub(" ", clean)
    clean = TEAM_INLINE_CONTACT_RE.sub(" ", clean)
    clean = TEAM_SECONDARY_ROLE_RE.sub(" ", clean)
    return normalize_space(repair_member_archive_names(clean))


def normalized_member_name_word(word: str) -> str:
    if word.islower() or word.isupper():
        return word[:1].upper() + word[1:].lower()
    return word


def repair_member_archive_names(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        words = [match.group("label"), *match.group("rest").split()]
        return " ".join(normalized_member_name_word(word) for word in words)

    return MEMBER_ARCHIVE_NAME_RE.sub(replace, text)


def clean_team_professional(raw: str) -> str:
    clean = normalize_space(raw).strip(".,;:")
    titled = re.match(rf"^(?P<title>{TITLE_PREFIX})\s+(?P<name>.+)$", clean)
    if titled:
        return clean_titled_professional(titled)
    words = []
    for word in name_words(clean):
        clean_key = fold(word.rstrip("."))
        if clean_key in ROLE_START_KEYS or clean_key in TITLE_WORD_KEYS:
            break
        words.append(word)
    if len(words) >= 3 and fold(words[0]) == fold(words[1]):
        words = words[1:]
    if len(words) < 2:
        return ""
    return " ".join(words[:4])


def professional_key(value: str) -> str:
    clean = re.sub(rf"^(?:{TITLE_PREFIX})\s+", "", normalize_space(value), flags=re.I)
    return fold(clean)


def has_professional_title(value: str) -> bool:
    return bool(re.match(rf"^(?:{TITLE_PREFIX})\s+", normalize_space(value), flags=re.I))


def dedupe_professionals(names: list[str]) -> list[str]:
    positions: dict[str, int] = {}
    result: list[str] = []
    for name in names:
        key = professional_key(name)
        if not key:
            continue
        if key not in positions:
            positions[key] = len(result)
            result.append(name)
            continue
        index = positions[key]
        if has_professional_title(name) and not has_professional_title(result[index]):
            result[index] = name
    return result


def extract_contacts(text: str) -> dict[str, list[str]]:
    emails = unique(EMAIL_RE.findall(text))
    phones = unique([
        phone
        for match in PHONE_RE.finditer(text)
        for phone in split_phone_candidate(match.group(0))
    ])
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
    professionals: list[tuple[int, str]] = []
    clean_text = strip_team_ctas(text)
    for match in TITLE_SCAN_RE.finditer(clean_text):
        clean = clean_titled_name(match.group("title"), title_name_segment(clean_text, match.end()))
        if clean:
            professionals.append((match.start(), clean))
    team_window = strip_team_ctas(professional_team_window(text))
    team_offset = clean_text.find(team_window) if team_window else 0
    for match in TEAM_ROLE_PAIR_RE.finditer(team_window):
        clean = clean_team_professional(match.group("name"))
        if clean:
            professionals.append((team_offset + match.start("name"), clean))
    return dedupe_professionals(unique([name for _, name in sorted(professionals, key=lambda item: item[0])]))


def extract_transparency(text: str, professionals: list[str]) -> dict[str, Any]:
    transparency: dict[str, Any] = {}
    years_label = extract_years_in_practice(text)
    if years_label:
        transparency["years_in_practice"] = years_label

    specialists_match = SPECIALISTS_COUNT_RE.search(text)
    if specialists_match:
        count = int(specialists_match.group("count"))
        if 1 <= count <= 300:
            transparency["specialists_count"] = count

    if TEAM_CREDENTIALING_RE.search(text):
        transparency["team_credentialing_visible"] = "si" if professionals else "parcial"

    if PUBLIC_PRICING_RE.search(text):
        transparency["public_pricing"] = "si"

    return transparency


def extract_years_in_practice(text: str) -> str | None:
    years_match = YEARS_IN_PRACTICE_RE.search(text)
    if years_match:
        years = int(years_match.group("years"))
        prefix = normalize_space(years_match.group("prefix") or "").lower()
        label = f"{years} años"
        if prefix in {"más de", "mas de", "over", "more than"}:
            label = f"más de {label}"
        return label

    decade_match = DECADE_IN_PRACTICE_RE.search(text)
    if not decade_match:
        return None
    raw_decades = fold(decade_match.group("decades"))
    decades = int(raw_decades) if raw_decades.isdigit() else DECADE_WORDS.get(raw_decades, 0)
    if decades < 1 or decades > 10:
        return None
    years = decades * 10
    prefix = normalize_space(decade_match.group("prefix") or "").lower()
    if prefix in {"más de", "mas de", "over", "more than"}:
        return f"más de {years} años"
    return f"{years} años"


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


def plausible_clinic_name(value: str) -> bool:
    clean = normalize_space(value)
    if not clean:
        return False
    words = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", clean)
    if len(words) < 1 or len(words) > 8:
        return False
    lower_words = {word.lower() for word in words}
    if lower_words & TITLE_NOISE_TERMS:
        return False
    return bool(lower_words & CLINIC_NAME_TERMS)


def summary_sentences(text: str) -> list[str]:
    clean = normalize_space(text)
    if not clean:
        return []
    return [
        normalize_space(part).strip(" -–—|:;")
        for part in re.split(r"(?<=[.!?])\s+", clean)
        if normalize_space(part)
    ]


def clean_summary_candidate(value: str) -> str:
    clean = normalize_space(value).strip(" -–—|:;")
    clean = re.sub(
        r"^(?:[A-ZÁÉÍÓÚÜÑ0-9&,'’/-]+\s+){3,}(?=[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ])",
        "",
        clean,
    )
    return normalize_space(clean).strip(" -–—|:;")


def truncate_summary(value: str) -> str:
    clean = normalize_space(value)
    if len(clean) <= SUMMARY_MAX_CHARS:
        return clean
    truncated = clean[:SUMMARY_MAX_CHARS].rsplit(" ", 1)[0]
    return normalize_space(truncated).strip(" ,.;:")


def summary_score(candidate: str) -> int:
    clean = normalize_space(candidate)
    if len(clean) < SUMMARY_MIN_CHARS or SUMMARY_NOISE_RE.search(clean):
        return -1
    folded = fold(clean)
    if not any(term in folded for term in SUMMARY_SIGNAL_TERMS):
        return -1
    score = 0
    score += sum(1 for term in SUMMARY_SIGNAL_TERMS if term in folded)
    if any(term in folded for term in SUMMARY_SPANISH_TERMS):
        score += 2
    if any(term in folded for term in ("tiara health", "longevity", "longevidad", "clinic", "clínica", "clinica")):
        score += 2
    if SUMMARY_MIN_CHARS <= len(clean) <= SUMMARY_MAX_CHARS:
        score += 1
    return score


def extract_summary(text: str, title: str = "", source_url: str = "") -> str | None:
    if source_url_title_looks_like_team_page(source_url, title):
        return None
    sentences = summary_sentences(text)
    candidates: list[tuple[int, int, str]] = []
    for index, sentence in enumerate(sentences):
        clean = clean_summary_candidate(sentence)
        score = summary_score(clean)
        if score >= 0:
            candidates.append((score, -index, truncate_summary(clean)))
    if not candidates:
        for index in range(max(0, len(sentences) - 1)):
            clean = clean_summary_candidate(" ".join(sentences[index : index + 2]))
            score = summary_score(clean)
            if score >= 0:
                candidates.append((score, -index, truncate_summary(clean)))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][2]


def claim(field_path: str, value: Any, confidence: float, source_url: str) -> dict[str, Any]:
    return {
        "field_path": field_path,
        "value": value,
        "confidence": confidence,
        "source_count": 1,
        "source_url": source_url,
        "verifier_verdict": "unknown",
        "agent_name": "vitalarga-shadow-extractor",
        "agent_version": "2026-08-30",
    }


def build_claims(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    source_url = str(snapshot.get("final_url") or snapshot.get("source_url") or "")
    text = normalize_space(str(snapshot.get("text_excerpt") or ""))
    contacts = extract_contacts(text)
    professionals = extract_professionals(text)
    locations = extract_locations(text)
    transparency = extract_transparency(text, professionals)
    keywords = detect_keywords(text)
    summary = extract_summary(text, str(snapshot.get("source_title") or ""), source_url)
    claims: list[dict[str, Any]] = []

    name = guess_name(snapshot)
    if plausible_clinic_name(name):
        claims.append(claim("identity.canonical_name", name, 0.55, source_url))
    if source_url:
        parsed = urlparse(source_url)
        claims.append(claim("contact.website", f"{parsed.scheme}://{parsed.netloc}", 0.86, source_url))
    if summary:
        claims.append(claim("profile.summary", summary, 0.64, source_url))
    if contacts["emails"]:
        claims.append(claim("contact.email", contacts["emails"][0], 0.88, source_url))
    if contacts["phones"]:
        primary_phone = contacts["phones"][0]
        claims.append(claim("contact.phone", primary_phone, 0.78, source_url))
        primary_digits = {spanish_phone_digits(primary_phone)}
        fixed_phone = first_phone_by_kind(contacts["phones"], "fixed", primary_digits)
        mobile_phone = first_phone_by_kind(contacts["phones"], "mobile", primary_digits)
        if fixed_phone:
            claims.append(claim("contact.phone_fixed", fixed_phone, 0.78, source_url))
        if mobile_phone:
            claims.append(claim("contact.phone_mobile", mobile_phone, 0.78, source_url))
    if contacts["instagram"]:
        claims.append(claim("contact.instagram", contacts["instagram"][0], 0.80, source_url))
    if locations:
        claims.append(claim("location.locations", locations[:MAX_LOCATIONS], 0.66, source_url))
    if professionals:
        claims.append(claim("professionals.published", professionals[:MAX_PROFESSIONALS], 0.64, source_url))
    if transparency.get("years_in_practice"):
        claims.append(claim("transparency.years_in_practice", transparency["years_in_practice"], 0.68, source_url))
    if transparency.get("specialists_count"):
        claims.append(claim("transparency.specialists_count", transparency["specialists_count"], 0.68, source_url))
    if transparency.get("team_credentialing_visible"):
        claims.append(claim("team.credentialing_visible", transparency["team_credentialing_visible"], 0.62, source_url))
    if transparency.get("public_pricing"):
        claims.append(claim("prices.public_status", transparency["public_pricing"], 0.62, source_url))
    for field_path, values in keywords.items():
        if values:
            claims.append(claim(field_path, values, 0.70, source_url))
    return claims


def build_profile(snapshot: dict[str, Any]) -> dict[str, Any]:
    text = normalize_space(str(snapshot.get("text_excerpt") or ""))
    contacts = extract_contacts(text)
    professionals = extract_professionals(text)
    locations = extract_locations(text)
    transparency = extract_transparency(text, professionals)
    keywords = detect_keywords(text)
    name = guess_name(snapshot)
    summary = extract_summary(text, str(snapshot.get("source_title") or ""), str(snapshot.get("final_url") or snapshot.get("source_url") or ""))
    profile = {
        "name": name if plausible_clinic_name(name) else None,
        "summary": summary,
        "website": claim_website(str(snapshot.get("final_url") or snapshot.get("source_url") or "")),
        "emails": contacts["emails"],
        "phones": contacts["phones"],
        "instagram": contacts["instagram"],
        "locations": locations[:MAX_LOCATIONS],
        "services": keywords.get("services.list", []),
        "specialties": keywords.get("specialties.list", []),
        "units": keywords.get("units.list", []),
        "professionals": professionals[:MAX_PROFESSIONALS],
        "years_in_practice": transparency.get("years_in_practice"),
        "specialists_count": transparency.get("specialists_count"),
        "team_credentialing_visible": transparency.get("team_credentialing_visible"),
        "public_pricing": transparency.get("public_pricing"),
        "technologies": keywords.get("technologies.list", []),
    }
    return {key: value for key, value in profile.items() if value}


def claim_website(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return None


def extract_from_fetch(result: FetchResult) -> dict[str, Any]:
    snapshot = extraction_snapshot_from_fetch(result)
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
