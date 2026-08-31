#!/usr/bin/env python3
"""Explain why one Vitalarga clinic is or is not current on the public site."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any

from admin_digest import parse_timestamp
from check_public_site_freshness import run_freshness_check
from clinic_publication_readiness import (
    PUBLIC_STATUSES,
    load_readiness,
    missing_required_fields,
    next_publication_step,
    status_label,
    visibility_message,
)
from submit_discovery_candidates import load_env_file


FIELD_LABELS = {
    "email": "email",
    "instagram": "Instagram",
    "telefono": "teléfono",
    "phone": "teléfono",
    "services": "servicios",
    "specialties": "especialidades",
    "unidades": "unidades",
    "profesionales": "especialistas",
    "locations": "sedes",
    "tech": "tecnología",
    "years_in_practice": "años en ejercicio",
    "specialists_count": "número de especialistas",
    "team_credentialing_visible": "colegiación visible",
    "public_pricing": "precio público",
}


def public_status(status: Any) -> bool:
    return str(status or "") in PUBLIC_STATUSES


def first_dict(rows: Any) -> dict[str, Any]:
    if not isinstance(rows, list):
        return {}
    for row in rows:
        if isinstance(row, dict):
            return row
    return {}


def stale_freshness_check(report: dict[str, Any]) -> dict[str, Any]:
    for row in report.get("checks") or []:
        if isinstance(row, dict) and not row.get("fresh"):
            return row
    return {}


def missing_field_groups(check: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    for item in check.get("missing_examples") or []:
        if not isinstance(item, dict):
            continue
        field = str(item.get("field") or "").split(".", 1)[0]
        label = FIELD_LABELS.get(field, field or "campo")
        if label not in seen:
            labels.append(label)
            seen.add(label)
    return labels


def load_visibility_report(
    clinic_query: str,
    base_url: str,
    timeout: int,
    missing_limit: int,
    local_env: dict[str, str],
) -> dict[str, Any]:
    readiness = load_readiness(clinic_query, 5, local_env)
    freshness: dict[str, Any] = {}
    freshness_error = ""
    try:
        freshness = run_freshness_check(
            base_url=base_url,
            timeout=timeout,
            slug="",
            missing_limit=missing_limit,
            clinic_query=clinic_query,
        )
    except Exception as exc:  # pragma: no cover - covered by formatter tests.
        freshness_error = str(exc)
    return {
        "query": clinic_query,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "writes_data": False,
        "readiness": readiness,
        "freshness": freshness,
        "freshness_error": freshness_error,
    }


def format_visibility_report(report: dict[str, Any]) -> str:
    readiness = report.get("readiness") or {}
    matches = [row for row in readiness.get("matches") or [] if isinstance(row, dict)]
    clinic = first_dict(matches)
    freshness = report.get("freshness") or {}
    stale_check = stale_freshness_check(freshness)
    freshness_error = str(report.get("freshness_error") or "").strip()
    lines = [
        "# Vitalarga clinic visibility report",
        "",
        f"Generado: {parse_timestamp(report.get('generated_at'))}",
        f"Consulta: {report.get('query') or '-'}",
        "- Writes data: no",
        "",
    ]
    if not clinic:
        lines.extend(
            [
                "## Diagnóstico",
                "- No he encontrado una clínica con ese nombre o slug en Supabase.",
                "- Siguiente paso: revisar el nombre escrito o buscarla desde el panel de clínicas.",
            ]
        )
        return "\n".join(lines) + "\n"

    name = clinic.get("clinic_name") or clinic.get("slug") or "Clínica sin nombre"
    status = str(clinic.get("status") or "")
    missing = missing_required_fields(clinic)
    lines.extend(
        [
            "## Clínica",
            f"- Nombre: {name}",
            f"- Estado interno: {status_label(status)}",
            f"- Última edición guardada: {parse_timestamp(clinic.get('updated_at'))}",
            f"- Visibilidad esperada: {visibility_message(clinic)}",
            "",
            "## Diagnóstico",
        ]
    )
    if not public_status(status):
        lines.append(
            f"- No aparece en la web pública porque está como {status_label(status)}."
        )
        lines.append(
            f"- Siguiente paso: {next_publication_step(clinic, missing)}"
        )
    elif stale_check:
        groups = missing_field_groups(stale_check)
        missing_count = int(stale_check.get("missing_markers") or 0)
        lines.append("- Está guardada en Supabase, pero la web visible va por detrás.")
        lines.append(
            f"- Diferencia detectada: {missing_count} campos guardados todavía no aparecen online."
        )
        if groups:
            lines.append(f"- Campos afectados: {', '.join(groups)}.")
        lines.append(
            "- Siguiente paso: actualizar la web pública solo cuando Daniel decida asumir ese rebuild de Netlify."
        )
    elif freshness_error:
        lines.append("- No he podido comparar contra la web pública ahora mismo.")
        lines.append(f"- Motivo técnico: {freshness_error[:180]}.")
        lines.append("- Siguiente paso: repetir la comprobación cuando haya acceso de red.")
    else:
        lines.append("- No detecto desfase en los campos públicos medidos.")
        if missing:
            lines.append(f"- Aun así, falta para dejarla lista: {', '.join(missing)}.")
            lines.append(f"- Siguiente paso: {next_publication_step(clinic, missing)}")
        else:
            lines.append("- Siguiente paso: no hay bloqueo obligatorio detectado.")

    if missing and public_status(status):
        lines.extend(
            [
                "",
                "## Para dejar la ficha completa",
                f"- Falta: {', '.join(missing)}.",
                f"- Siguiente paso: {next_publication_step(clinic, missing)}",
            ]
        )
    lines.extend(
        [
            "",
            "Nota: este informe no publica, no edita clínicas y no toca Netlify.",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clinic", required=True, help="Clinic name or slug.")
    parser.add_argument("--base-url", default="https://www.vitalarga.com")
    parser.add_argument("--timeout", type=int, default=12)
    parser.add_argument("--missing-limit", type=int, default=30)
    parser.add_argument("--json", action="store_true", help="Print raw JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.timeout < 3 or args.timeout > 60:
        raise SystemExit("--timeout must be between 3 and 60 seconds.")
    if args.missing_limit < 1 or args.missing_limit > 30:
        raise SystemExit("--missing-limit must be between 1 and 30.")
    report = load_visibility_report(
        args.clinic.strip(),
        args.base_url,
        args.timeout,
        args.missing_limit,
        load_env_file(),
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_visibility_report(report), end="")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
