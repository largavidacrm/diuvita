#!/usr/bin/env python3
"""Export reviewable specialist proposals from internal field claims.

This script is read-only against Supabase. It prepares a proposal batch that can
later be reviewed and submitted as internal review_queue cards; it does not edit
clinic records, resolve reviews or publish public pages.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from admin_digest import as_int, plural
from specialist_review_reconciliation import load_reconciliation
from submit_discovery_candidates import load_env_file


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRIORITY = 55


def today_batch_name(now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    return f"specialist-claim-proposals-{current.date().isoformat()}"


def clean_sources(values: Any) -> list[str]:
    if not isinstance(values, list):
        values = [values]
    sources: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = str(value or "").strip()
        if not clean.lower().startswith(("http://", "https://")):
            continue
        key = clean.lower()
        if key in seen:
            continue
        seen.add(key)
        sources.append(clean)
    return sources


def proposal_from_row(row: dict[str, Any], include_existing_cards: bool = False) -> dict[str, Any] | None:
    pending = [str(item).strip() for item in row.get("pending_professionals") or [] if str(item).strip()]
    if not pending:
        return None
    if as_int(row.get("review_card_count")) and not include_existing_cards:
        return None
    slug = str(row.get("slug") or "").strip()
    if not slug:
        return None
    name = str(row.get("clinic_name") or slug).strip()
    sources = clean_sources(row.get("claim_source_urls_clean") or row.get("claim_source_urls") or [])
    proposal = {
        "slug": slug,
        "title": f"Ampliar especialistas: {name}",
        "priority": DEFAULT_PRIORITY,
        "source_url": sources[0] if sources else "",
        "source_urls": sources,
        "proposed_fields": {
            "profesionales": pending,
        },
        "warnings": [
            "Especialistas propuestos desde evidencias internas; revisar fuente pública antes de guardar.",
        ],
    }
    return proposal


def build_export(
    report: dict[str, Any],
    batch: str | None = None,
    include_existing_cards: bool = False,
) -> dict[str, Any]:
    proposals: list[dict[str, Any]] = []
    skipped_with_cards = 0
    skipped_without_pending = 0
    for row in report.get("clinics") or []:
        if not isinstance(row, dict):
            continue
        if not as_int(row.get("pending_professional_count")):
            skipped_without_pending += 1
            continue
        if as_int(row.get("review_card_count")) and not include_existing_cards:
            skipped_with_cards += 1
            continue
        proposal = proposal_from_row(row, include_existing_cards)
        if proposal:
            proposals.append(proposal)
    return {
        "batch": batch or today_batch_name(),
        "writes_data": False,
        "source": "field_claims",
        "summary": {
            "proposal_count": len(proposals),
            "skipped_with_open_cards": skipped_with_cards,
            "skipped_without_pending_names": skipped_without_pending,
        },
        "proposals": proposals,
    }


def format_export(export: dict[str, Any]) -> str:
    proposals = [item for item in export.get("proposals") or [] if isinstance(item, dict)]
    summary = export.get("summary") or {}
    lines = [
        "# Vitalarga: propuestas de especialistas",
        "",
        f"- Lote: {export.get('batch')}",
        "- Writes data: no",
        f"- Propuestas listas: {as_int(summary.get('proposal_count'))}",
        f"- Omitidas por tener tarjeta abierta: {as_int(summary.get('skipped_with_open_cards'))}",
        f"- Sin nombres pendientes: {as_int(summary.get('skipped_without_pending_names'))}",
        "",
        "## Fichas preparadas",
    ]
    if not proposals:
        lines.append("- No hay propuestas nuevas que preparar.")
    for proposal in proposals:
        fields = proposal.get("proposed_fields") or {}
        people = fields.get("profesionales") if isinstance(fields, dict) else []
        count = len(people) if isinstance(people, list) else 0
        sources = proposal.get("source_urls") if isinstance(proposal.get("source_urls"), list) else []
        lines.append(
            "- "
            + str(proposal.get("slug") or "sin-slug")
            + f": {count} {plural(count, 'especialista', 'especialistas')}, "
            + f"{len(sources)} {plural(len(sources), 'fuente', 'fuentes')}, "
            + f"P{as_int(proposal.get('priority'))}"
        )
    lines.extend([
        "",
        "Nota: esto prepara propuestas internas. Crear tarjetas de revisión requiere un paso aparte y sigue sin publicar datos.",
    ])
    return "\n".join(lines) + "\n"


def assert_safe_output_path(path: Path, allow_repo_output: bool = False) -> Path:
    resolved = path.expanduser().resolve()
    repo = ROOT.resolve()
    if not allow_repo_output and (resolved == repo or repo in resolved.parents):
        raise SystemExit("Por seguridad, escribe este lote fuera del repositorio, por ejemplo en /tmp.")
    return resolved


def write_export(export: dict[str, Any], path: Path, allow_repo_output: bool = False) -> Path:
    target = assert_safe_output_path(path, allow_repo_output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(export, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clinic", default="", help="Optional clinic name or slug.")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--batch", default="", help="Optional proposal batch name.")
    parser.add_argument(
        "--include-existing-cards",
        action="store_true",
        help="Also export clinics that already have open specialist review cards.",
    )
    parser.add_argument("--json", action="store_true", help="Print proposal JSON, including proposed names.")
    parser.add_argument("--output", default="", help="Optional JSON output path. Prefer /tmp for private batches.")
    parser.add_argument(
        "--allow-repo-output",
        action="store_true",
        help="Allow writing the generated proposal batch inside the repository.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1.")
    report = load_reconciliation(args.clinic, args.limit, load_env_file())
    export = build_export(
        report,
        batch=args.batch or None,
        include_existing_cards=args.include_existing_cards,
    )
    if args.output:
        target = write_export(export, Path(args.output), args.allow_repo_output)
        print(f"Lote escrito: {target}")
    if args.json:
        print(json.dumps(export, ensure_ascii=False, indent=2))
    else:
        print(format_export(export), end="")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
