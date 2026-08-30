#!/usr/bin/env python3
"""Print a read-only brief for blocking Vitalarga field claims."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from typing import Any
from urllib.parse import urlparse

from admin_digest import parse_timestamp
from submit_blocking_claim_reviews import load_blocking_claim_groups, priority_for_claims
from submit_discovery_candidates import load_env_file


FIELD_LABELS = {
    "identity.canonical_name": "Nombre",
    "profile.name": "Nombre",
    "contact.website": "Web",
    "location.country": "País",
    "location.city": "Ciudad",
    "location.region": "Región",
    "location.address": "Dirección",
    "summary": "Resumen",
    "services.list": "Servicios",
    "specialties.list": "Especialidades",
    "diagnostics.list": "Diagnósticos",
    "programs.list": "Programas",
    "units.list": "Unidades",
    "professionals.published": "Especialistas",
    "team.public_professionals": "Especialistas",
    "team.credentials": "Credenciales",
    "technologies.list": "Tecnología",
    "contact.email": "Email",
    "contact.phone": "Teléfono",
    "contact.instagram": "Instagram",
    "prices.list": "Precios",
    "treatments.list": "Tratamientos",
    "medical_claims.list": "Claims médicos",
    "outcomes.list": "Resultados",
    "evidence.list": "Evidencia clínica",
}

STATUS_LABELS = {
    "conflict": "en conflicto",
    "rejected": "rechazado",
    "without_source": "sin fuente",
    "review": "en revisión",
    "proposed": "propuesto",
    "stale": "fuente antigua",
}

STATUS_COUNT_LABELS = {
    "conflict": ("en conflicto", "en conflicto"),
    "rejected": ("rechazado", "rechazados"),
    "without_source": ("sin fuente", "sin fuente"),
    "review": ("en revisión", "en revisión"),
    "proposed": ("propuesto", "propuestos"),
    "stale": ("con fuente antigua", "con fuente antigua"),
}


def as_claims(group: dict[str, Any]) -> list[dict[str, Any]]:
    return [claim for claim in group.get("claims") or [] if isinstance(claim, dict)]


def field_label(field_path: Any) -> str:
    path = str(field_path or "").strip()
    return FIELD_LABELS.get(path, path.replace("_", " ") or "Campo")


def blocker_status(claim: dict[str, Any]) -> str:
    return str(claim.get("blocker_status") or claim.get("verification_status") or "review")


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status.replace("_", " "))


def pct(value: Any) -> str:
    try:
        return f"{round(float(value or 0) * 100)}%"
    except (TypeError, ValueError):
        return "-"


def source_host(url: Any) -> str:
    clean = str(url or "").strip()
    if not clean:
        return "sin fuente"
    host = urlparse(clean).netloc or clean
    return host.replace("www.", "") or clean


def summarize_group(group: dict[str, Any]) -> dict[str, Any]:
    claims = as_claims(group)
    counts = Counter(blocker_status(claim) for claim in claims)
    return {
        "clinic_slug": group.get("clinic_slug"),
        "clinic_name": group.get("clinic_name"),
        "clinic_city": group.get("clinic_city"),
        "clinic_country": group.get("clinic_country"),
        "website": group.get("website"),
        "priority": priority_for_claims(claims),
        "claims": len(claims),
        "statuses": dict(counts),
        "fields": [
            {
                "field": field_label(claim.get("field_path")),
                "field_path": claim.get("field_path"),
                "status": blocker_status(claim),
                "confidence": claim.get("confidence"),
                "source": source_host(claim.get("source_url")),
                "created_at": claim.get("created_at"),
            }
            for claim in claims
        ],
    }


def format_status_counts(statuses: dict[str, int]) -> str:
    parts = []
    for status in ["conflict", "rejected", "without_source", "stale", "review", "proposed"]:
        count = int(statuses.get(status) or 0)
        if count:
            singular, plural = STATUS_COUNT_LABELS.get(status, (status_label(status), status_label(status)))
            parts.append(f"{count} {singular if count == 1 else plural}")
    return " · ".join(parts) if parts else "sin detalle"


def recommended_step(statuses: dict[str, int]) -> str:
    if int(statuses.get("conflict") or 0):
        return "comparar la evidencia y elegir el dato correcto antes de publicar"
    if int(statuses.get("rejected") or 0):
        return "mantener el dato fuera de publicación o corregirlo con fuente mejor"
    if int(statuses.get("without_source") or 0):
        return "buscar una fuente oficial o quitar el dato propuesto"
    if int(statuses.get("stale") or 0):
        return "actualizar la fuente antes de aceptar el dato"
    return "revisar Evidencias propuestas antes de guardar"


def plural_claims(count: int) -> str:
    return f"{count} claim" if count == 1 else f"{count} claims"


def compact_field_rows(fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for field in fields:
        key = (
            str(field.get("field") or "Campo"),
            str(field.get("status") or "review"),
            str(field.get("source") or "sin fuente"),
            pct(field.get("confidence")),
        )
        current = grouped.get(key)
        created_at = field.get("created_at")
        if not current:
            grouped[key] = {
                "field": key[0],
                "status": key[1],
                "source": key[2],
                "confidence": key[3],
                "created_at": created_at,
                "count": 1,
            }
        else:
            current["count"] += 1
            if str(created_at or "") > str(current.get("created_at") or ""):
                current["created_at"] = created_at
    return sorted(grouped.values(), key=lambda item: (-int(item["count"]), str(item["field"])))


def format_brief(groups: list[dict[str, Any]]) -> str:
    summaries = [summarize_group(group) for group in groups]
    total_claims = sum(int(item["claims"]) for item in summaries)
    output = [
        "# Vitalarga: claims bloqueantes",
        "",
        f"- Clínicas afectadas: {len(summaries)}",
        f"- Claims a revisar: {total_claims}",
        "- Acción: abre el filtro Claims bloqueantes en el panel y revisa Evidencias propuestas.",
        "- Seguridad: este brief no publica, no edita fichas y no resuelve tarjetas.",
        "",
        "## Casos prioritarios",
    ]
    if not summaries:
        output.append("- No hay claims bloqueantes medidos.")
        return "\n".join(output) + "\n"

    for item in summaries:
        place = ", ".join(part for part in [item.get("clinic_city"), item.get("clinic_country")] if part)
        heading = str(item.get("clinic_name") or item.get("clinic_slug") or "Clinica")
        if place:
            heading += f" · {place}"
        output.append("")
        output.append(f"- {heading}")
        output.append(f"  Prioridad: P{item['priority']} · {plural_claims(int(item['claims']))} · {format_status_counts(item['statuses'])}")
        output.append(f"  Paso recomendado: {recommended_step(item['statuses'])}")
        if item.get("website"):
            output.append(f"  Web: {item['website']}")
        field_rows = compact_field_rows(item["fields"])
        for field in field_rows[:5]:
            created = parse_timestamp(field.get("created_at"))
            repeated = f" · {plural_claims(int(field['count']))}" if int(field.get("count") or 0) > 1 else ""
            output.append(
                "  Campo: "
                f"{field['field']} · {status_label(str(field['status']))} · "
                f"confianza {field['confidence']} · fuente {field['source']} · {created}{repeated}"
            )
        if len(field_rows) > 5:
            output.append(f"  Más campos: {len(field_rows) - 5}")
    return "\n".join(output) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--json", action="store_true", help="Print raw JSON instead of the plain brief.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1.")
    local_env = load_env_file()
    groups = load_blocking_claim_groups(args.limit, local_env)
    if args.json:
        print(json.dumps({
            "mode": "read_only",
            "groups_seen": len(groups),
            "total_claims": sum(len(as_claims(group)) for group in groups),
            "items": [summarize_group(group) for group in groups],
        }, ensure_ascii=False, indent=2))
    else:
        print(format_brief(groups), end="")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
