#!/usr/bin/env python3
"""Scan public Diuvita content for obvious operational-limit red flags."""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class GuardrailRule:
    limit: str
    name: str
    pattern: re.Pattern[str]
    reason: str


RULES = [
    GuardrailRule(
        "L2",
        "Recomendaciones médicas",
        re.compile(
            r"\b(?:la mejor opción para ti|te conviene|deber[ií]as hacerte|"
            r"recomendamos (?:que|hacerte|la|el|este|esta))\b",
            re.I,
        ),
        "posible consejo médico individual o recomendación directa",
    ),
    GuardrailRule(
        "L3",
        "Rankings y comparativas",
        re.compile(
            r"\b(?:top\s+\d+|ranking(?:s)? de cl[ií]nicas|rankings? de calidad|"
            r"mejores cl[ií]nicas|la mejor cl[ií]nica|estrellas)\b",
            re.I,
        ),
        "posible ranking o comparación de calidad",
    ),
    GuardrailRule(
        "L4",
        "Claims terapéuticos",
        re.compile(
            r"\b(?:cura(?:r|n)?|revierte|revertir el envejecimiento|rejuvenece|"
            r"alarga la vida|garantiza resultados?|garantizado)\b",
            re.I,
        ),
        "posible claim terapéutico no atributivo",
    ),
    GuardrailRule(
        "L5",
        "Testimonios y pacientes",
        re.compile(r"\b(?:testimonios? de pacientes|antes/despu[eé]s|antes\/despu[eé]s|casos cl[ií]nicos)\b", re.I),
        "posible contenido de pacientes, testimonios o antes/después",
    ),
    GuardrailRule(
        "L8",
        "Monetización y publicidad",
        re.compile(r"\b(?:enlace patrocinado|enlaces patrocinados|afiliaci[oó]n|pago por aparecer)\b", re.I),
        "posible publicidad, patrocinio o afiliación",
    ),
]

NEGATION_RE = re.compile(r"\b(?:no|sin|nunca|ning[uú]n|ninguna|evita(?:r)?|evitamos|prohibid[oa]s?)\b", re.I)


def public_content_paths() -> list[Path]:
    paths = [ROOT / "data" / "clinics.json", ROOT / "build.py"]
    posts_dir = ROOT / "data" / "posts"
    if posts_dir.exists():
        paths.extend(sorted(posts_dir.glob("*.md")))
    return [path for path in paths if path.exists()]


def is_negated_context(line: str, match_start: int) -> bool:
    before = line[max(0, match_start - 90):match_start]
    return bool(NEGATION_RE.search(before))


def scan_text(path: Path, content: str) -> list[str]:
    findings: list[str] = []
    for line_no, line in enumerate(content.splitlines(), start=1):
        for rule in RULES:
            for match in rule.pattern.finditer(line):
                if is_negated_context(line, match.start()):
                    continue
                findings.append(
                    f"{path.relative_to(ROOT)}:{line_no}: {rule.limit} {rule.name}: "
                    f"{rule.reason}: {match.group(0)!r}"
                )
    return findings


def main() -> int:
    findings: list[str] = []
    for path in public_content_paths():
        findings.extend(scan_text(path, path.read_text(encoding="utf-8")))

    if findings:
        print("FAIL operational limits: public content needs review")
        for finding in findings:
            print(f"  {finding}")
        return 1

    print("OK operational limits: no obvious public red flags")
    return 0


if __name__ == "__main__":
    sys.exit(main())
