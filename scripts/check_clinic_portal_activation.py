#!/usr/bin/env python3
"""Print a read-only activation checklist for the Vitalarga clinic portal."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ActivationCheck:
    key: str
    label: str
    status: str
    detail: str


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def has_all(text: str, markers: list[str]) -> bool:
    return all(marker in text for marker in markers)


def code_check(key: str, label: str, ok: bool, ready_detail: str, blocked_detail: str) -> ActivationCheck:
    return ActivationCheck(
        key=key,
        label=label,
        status="ready" if ok else "blocked",
        detail=ready_detail if ok else blocked_detail,
    )


def manual_check(key: str, label: str, approved: bool, ready_detail: str, manual_detail: str) -> ActivationCheck:
    return ActivationCheck(
        key=key,
        label=label,
        status="ready" if approved else "manual",
        detail=ready_detail if approved else manual_detail,
    )


def build_checks(approvals: dict[str, bool] | None = None) -> list[ActivationCheck]:
    approvals = approvals or {}
    migration = read("supabase/migrations/0023_clinic_portal.sql")
    build = read("build.py")
    admin = read("admin/index.html")
    portal_html = read("portal-clinicas/index.html")
    portal_js = read("portal-clinicas/portal.js")
    docs = read("docs/CLINIC_PORTAL.md")
    combined_portal = portal_html + "\n" + portal_js
    combined_public = build + "\n" + portal_html + "\n" + admin

    checks = [
        code_check(
            "portal_public_route",
            "Ruta pública del portal",
            has_all(
                build,
                [
                    "def write_clinic_portal():",
                    "def portal_clinic_list():",
                    '"/portal-clinicas/"',
                    "write_clinic_portal()",
                ],
            )
            and has_all(
                portal_html,
                [
                    "Portal de clínicas",
                    "window.VITALARGA_PORTAL_CONFIG",
                    "window.VITALARGA_PORTAL_CLINICS",
                ],
            ),
            "La página /portal-clinicas/ se genera en el sitio estático.",
            "Falta cableado local para generar /portal-clinicas/.",
        ),
        code_check(
            "manual_review_data_model",
            "Modelo de revisión manual",
            has_all(
                migration,
                [
                    "create table if not exists public.clinic_claim_requests",
                    "create table if not exists public.clinic_portal_memberships",
                    "create table if not exists public.clinic_profile_change_requests",
                    "enable row level security",
                    "portal_submit_clinic_claim_request",
                    "portal_submit_profile_change_request",
                    "admin_resolve_clinic_claim_request",
                    "admin_resolve_clinic_profile_change_request",
                ],
            ),
            "La migración local crea solicitudes, membresías, propuestas de cambio y RLS.",
            "La migración local del portal está incompleta.",
        ),
        code_check(
            "public_intake_flows",
            "Flujos públicos de entrada",
            has_all(
                combined_portal,
                [
                    'id="claimForm"',
                    'id="recommendForm"',
                    'p_request_kind: "claim_existing"',
                    'p_request_kind: "recommend_clinic"',
                    "portal_submit_clinic_claim_request",
                ],
            ),
            "El portal permite reclamar ficha y sugerir una clínica para revisión.",
            "Falta alguno de los formularios públicos del portal.",
        ),
        code_check(
            "private_workspace_flow",
            "Zona privada de clínica",
            has_all(
                combined_portal,
                [
                    'id="loginForm"',
                    'id="workspacePanel"',
                    'id="changeForm"',
                    "signInWithOtp",
                    "portal_my_clinic_workspace",
                    "portal_submit_profile_change_request",
                ],
            ),
            "La clínica aprobada puede entrar con enlace mágico y proponer cambios.",
            "Falta parte del acceso privado o de la propuesta de cambios.",
        ),
        code_check(
            "admin_resolution_flow",
            "Resolución desde el admin",
            has_all(
                admin,
                [
                    '["clinic_claim_request", "Reclamaciones"]',
                    "admin_resolve_clinic_claim_request",
                    "admin_resolve_clinic_profile_change_request",
                    "Pedir más información",
                    "Datos confirmados por el centro",
                ],
            ),
            "El admin puede aprobar, rechazar o pedir más información.",
            "El admin no tiene todas las acciones manuales del portal.",
        ),
        code_check(
            "operational_visibility",
            "Visibilidad operativa",
            has_all(
                migration + "\n" + admin + "\n" + read("scripts/admin_digest.py"),
                [
                    "'portal'",
                    "Portal clínicas",
                    "portal_status",
                    "next_portal_action",
                ],
            ),
            "Las solicitudes aparecen en panel, digest, brief y estado global.",
            "Falta visibilidad operativa de solicitudes del portal.",
        ),
        code_check(
            "safe_boundaries",
            "Límites de seguridad",
            'type="file"' not in portal_html.lower()
            and "smtp" not in portal_js.lower()
            and "Clínica Verificada" not in combined_public
            and has_all(
                combined_portal + "\n" + docs,
                [
                    "Nada se publica automáticamente",
                    "Deliberadamente fuera de esta fase",
                    "Emails salientes enviados por Vitalarga",
                ],
            ),
            "No hay subida de documentos, emails directos, distintivo fuerte ni publicación automática.",
            "Algún límite del portal necesita revisión antes de activar.",
        ),
        manual_check(
            "legal_privacy_review",
            "Revisión legal y privacidad",
            bool(approvals.get("legal_privacy_review")),
            "Daniel ha marcado como revisados los textos legales y de privacidad.",
            "Pendiente: Daniel debe revisar privacidad, base legal, retención y textos visibles antes de publicar el portal.",
        ),
        manual_check(
            "supabase_migration",
            "Migración Supabase",
            bool(approvals.get("supabase_migration")),
            "La migración del portal está marcada como aplicada en Supabase.",
            "Pendiente: aplicar la migración 0023 en Supabase solo cuando Daniel autorice tocar la base real.",
        ),
        manual_check(
            "supabase_auth",
            "Supabase Auth",
            bool(approvals.get("supabase_auth")),
            "Supabase Auth está marcado como configurado para enlaces mágicos del portal.",
            "Pendiente: configurar URLs permitidas, remitente y email de enlace mágico antes de aceptar accesos.",
        ),
        manual_check(
            "manual_flow_test",
            "Prueba real controlada",
            bool(approvals.get("manual_flow_test")),
            "Una prueba real de recomendación, reclamación y cambio de ficha está marcada como completada.",
            "Pendiente: probar un caso real controlado y confirmar que todo queda en revisión manual.",
        ),
        manual_check(
            "production_approval",
            "Aprobación de publicación",
            bool(approvals.get("production_approval")),
            "Daniel ha marcado la activación pública como aprobada.",
            "Pendiente: no publicar, empujar ni desplegar el portal sin aprobación expresa de Daniel.",
        ),
    ]
    return checks


def readiness(checks: list[ActivationCheck]) -> str:
    if any(check.status == "blocked" for check in checks):
        return "bloqueado técnicamente"
    if any(check.status == "manual" for check in checks):
        return "listo técnicamente; pendiente de decisión/manual"
    return "listo para activar cuando Daniel lo ordene"


def report_payload(checks: list[ActivationCheck]) -> dict[str, Any]:
    counts = {
        "ready": sum(1 for check in checks if check.status == "ready"),
        "manual": sum(1 for check in checks if check.status == "manual"),
        "blocked": sum(1 for check in checks if check.status == "blocked"),
    }
    return {
        "result": readiness(checks),
        "counts": counts,
        "checks": [asdict(check) for check in checks],
        "safety_note": "Este informe no activa Supabase, Netlify ni producción.",
    }


def format_report(payload: dict[str, Any]) -> str:
    output = [
        "# Vitalarga: activación del portal de clínicas",
        "",
        f"Resultado: {payload['result']}",
        "Seguridad: este informe no activa Supabase, Netlify ni producción.",
        "",
    ]
    for status, title in [
        ("blocked", "Bloqueos técnicos"),
        ("manual", "Pendiente de Daniel o configuración"),
        ("ready", "Listo localmente"),
    ]:
        rows = [item for item in payload["checks"] if item["status"] == status]
        if not rows:
            continue
        output.append(f"## {title}")
        for item in rows:
            output.append(f"- {item['label']}: {item['detail']}")
        output.append("")
    return "\n".join(output).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero unless every item is ready.")
    parser.add_argument("--legal-privacy-reviewed", action="store_true", help="Mark legal/privacy review as done for this report only.")
    parser.add_argument("--supabase-migration-applied", action="store_true", help="Mark the Supabase migration as applied for this report only.")
    parser.add_argument("--supabase-auth-configured", action="store_true", help="Mark Supabase Auth settings as configured for this report only.")
    parser.add_argument("--manual-flow-tested", action="store_true", help="Mark the controlled end-to-end portal test as done.")
    parser.add_argument("--production-approved", action="store_true", help="Mark Daniel's public activation approval as given.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    approvals = {
        "legal_privacy_review": args.legal_privacy_reviewed,
        "supabase_migration": args.supabase_migration_applied,
        "supabase_auth": args.supabase_auth_configured,
        "manual_flow_test": args.manual_flow_tested,
        "production_approval": args.production_approved,
    }
    payload = report_payload(build_checks(approvals))
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_report(payload), end="")
    if payload["counts"]["blocked"]:
        return 1
    if args.strict and (payload["counts"]["manual"] or payload["counts"]["blocked"]):
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
