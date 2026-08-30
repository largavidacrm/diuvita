#!/usr/bin/env python3
"""Checks that public clinic pages expose richer profile navigation/search UX."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    source = (ROOT / "build.py").read_text(encoding="utf-8")

    for marker in [
        "def profile_nav(",
        "def profile_nav_item(",
        "def profile_snapshot(",
        "def clinic_locations(",
        "def locations_block(",
        "def transparency_block(",
        "def location_maps_url(",
        "def location_reviews_url(",
        "def location_detail(",
        "def transparency_items(",
        'f\'<p>{h(detail or address or location_city(loc, c))}</p>\'',
        "def card_signal_html(",
        "def stat_items(",
        "def contact_count(",
        "def section_heading(",
        'class="card-signals"',
        'aria-label="Datos visibles de la ficha"',
        'class="profile-snapshot"',
        'aria-label="Resumen rápido de la ficha"',
        'class="profile-jump"',
        'class="profile-jump-label"',
        'class="profile-nav"',
        'aria-label="{h(label)}: {h(count)}"',
        'class="profile-nav-count" aria-hidden="true"',
        'id="sedes"',
        'class="location-list"',
        'class="location-actions"',
        'Valoraciones Google',
        'id="transparencia"',
        'class="transparency-grid"',
        'Años en ejercicio',
        'Número de especialistas',
        'Colegiación visible',
        'Precio público',
        'class="profile-section-head"',
        'class="section-count"',
        'class="profile-list"',
        'id="servicios"',
        'id="unidades"',
        'id="especialistas"',
        ".profile-sections{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem;margin-top:1.5rem;align-items:start}",
        ".profile-block{min-width:0;padding:1.05rem 1.1rem;border:1px solid var(--line);border-radius:8px;background:var(--surface);box-shadow:0 1px 0 rgba(23,35,31,.03)}",
        ".clinic-side .profile-block{margin-top:0;padding:0;border:0;border-radius:0;background:transparent;box-shadow:none}",
        ".profile-list li::before",
        ".location-list{display:grid;gap:.72rem}",
        ".mini-action{display:inline-flex;align-items:center;justify-content:center;min-height:1.9rem",
        ".transparency-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.55rem}",
        ".card-signals{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.45rem;margin-top:.85rem}",
        ".profile-snapshot{max-width:760px;display:grid;grid-template-columns:repeat(auto-fit,minmax(118px,1fr));gap:.55rem;margin-top:1rem}",
        ".clinic-side .visit{width:100%}",
        ".clinic-main{min-width:0}",
        ".ficha .loc{color:var(--coral);text-transform:uppercase;font-size:.86rem;font-weight:800;margin:.6rem 0 1rem;letter-spacing:0;overflow-wrap:anywhere}",
        ".profile-snapshot{grid-template-columns:repeat(2,minmax(0,1fr))}",
        ".profile-nav{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))}",
        'c.get("web", "")',
        'c.get("email", "")',
        'c.get("telefono", "")',
        'c.get("instagram", "")',
        'c.get("years_in_practice", "")',
        'c.get("specialists_count", "")',
        'c.get("team_credentialing_visible", "")',
        'c.get("public_pricing", "")',
        ".profile-block li{margin:.24rem 0}",
        '" ".join(c.get("unidades", []))',
        '" ".join(c.get("profesionales", []))',
        'c.get("tech", "")',
    ]:
        check(marker in source, f"missing public profile UX marker: {marker}")

    print("OK public profile UX: navigation and richer search wired")


if __name__ == "__main__":
    main()
