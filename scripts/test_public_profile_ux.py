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
        "def normalize_clinic(",
        'clinic.pop("internal_contact", None)',
        "def profile_nav(",
        "def profile_nav_item(",
        "def clinic_locations(",
        "def locations_block(",
        "def location_display_name(",
        "def transparency_block(",
        "def location_maps_url(",
        "def location_detail(",
        "def location_kind_value(",
        "def location_is_online(",
        "def care_mode_label(",
        "def contact_phone_items(",
        "def is_google_maps_profile_url(",
        "def transparency_items(",
        'f\'<p>{h(detail or address or location_city(loc, c))}</p>\'',
        "def card_signal_html(",
        "def stat_items(",
        "def contact_count(",
        "def section_heading(",
        'fallback_address = "" if explicit_clinic_locations(c) else c.get("address")',
        'hero_address = location_address(primary_location(c)) or (c.get("address") if not explicit_clinic_locations(c) and len(locations) <= 1 else "")',
        'class="card-signals"',
        'aria-label="Datos visibles de la ficha"',
        'class="profile-jump"',
        'class="profile-jump-label"',
        'class="profile-nav"',
        'aria-label="{h(label)}"',
        'id="sedes"',
        'profile-block profile-location-block',
        'profile-location-multiple',
        'class="location-list"',
        'class="location-actions"',
        'location_display_name(loc, c, multiple)',
        'id="transparencia"',
        'class="transparency-grid"',
        'Años en ejercicio',
        'Número de especialistas',
        'Colegiación visible',
        'Registro sanitario',
        'Nº colegiado',
        'Precio público',
        'Precio visita',
        'class="profile-section-head"',
        'class="profile-list"',
        'id="servicios"',
        'id="unidades"',
        'id="especialistas"',
        ".profile-sections{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem;margin-top:1.5rem;align-items:start}",
        ".profile-block{min-width:0;padding:1.05rem 1.1rem;border:1px solid var(--line);border-radius:8px;background:var(--surface);box-shadow:0 1px 0 rgba(23,35,31,.03)}",
        ".clinic-side .profile-block{margin-top:0;padding:0;border:0;border-radius:0;background:transparent;box-shadow:none}",
        ".profile-list li::before",
        ".location-list{display:grid;gap:.72rem}",
        ".profile-location-block{grid-column:1/-1;align-self:start}",
        ".profile-location-multiple{grid-column:1/-1}",
        ".profile-location-multiple .location-list{grid-template-columns:repeat(auto-fit,minmax(15rem,1fr));gap:.75rem}",
        ".profile-location-multiple .location-item{border:1px solid var(--line);border-radius:8px;padding:.85rem;background:#fff}",
        ".mini-action{display:inline-flex;align-items:center;justify-content:center;min-height:1.9rem",
        ".transparency-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.55rem}",
        ".card-signals{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.45rem;margin-top:.85rem}",
        ".clinic-side .visit{width:100%}",
        ".clinic-main{min-width:0}",
        ".ficha .loc{color:var(--coral);text-transform:uppercase;font-size:.86rem;font-weight:800;margin:.6rem 0 1rem;letter-spacing:0;overflow-wrap:anywhere}",
        ".profile-nav{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))}",
        'c.get("web", "")',
        'c.get("email", "")',
        'c.get("telefono", "")',
        'c.get("phone_fixed", "")',
        'c.get("phone_mobile", "")',
        'c.get("phone_whatsapp", "")',
        'c.get("care_mode", "")',
        'c.get("instagram", "")',
        'c.get("years_in_practice", "")',
        'c.get("specialists_count", "")',
        'c.get("team_credentialing_visible", "")',
        'c.get("clinic_registry_number", "")',
        'c.get("professional_license_numbers")',
        'c.get("public_pricing", "")',
        'c.get("visit_price", "")',
        'c.get("pricing_url", "")',
        ".profile-block li{margin:.24rem 0}",
        '" ".join(c.get("unidades", []))',
        '" ".join(c.get("profesionales", []))',
        'c.get("tech", "")',
        'placeholder="Busca por nombre, ciudad, especialidad o teléfono…"',
        r'function digits(value){return (value||"").replace(/\\D/g,"");}',
    ]:
        check(marker in source, f"missing public profile UX marker: {marker}")

    for removed_marker in [
        "def profile_snapshot(",
        "profile-snapshot",
        "profile-nav-count",
        "section-count",
        "Sede {index + 1}",
        "google_maps_search_url",
        "def location_reviews_url(",
        "Valoraciones Google",
    ]:
        check(removed_marker not in source, f"public profile should not render decorative counters: {removed_marker}")

    maps_body = source[source.index("def location_maps_url("):source.index("def location_detail(")]
    check("is_google_maps_profile_url" in maps_body, "Google Maps links should require direct clinic profile signal")
    check("google_maps_search_url" not in source, "public profiles should not generate generic Google Maps searches")
    check("location_address" not in maps_body, "Google Maps fallback should use clinic name, not street address")
    check("location_search_name" not in maps_body, "Google Maps fallback should not use location labels")
    check('return direct if is_google_maps_profile_url(direct) else ""' in maps_body, "public Google Maps buttons should disappear unless a direct profile link exists")

    profile_body = source[source.index("def ficha(c):"):source.index("def ciudad_page(city):")]
    check(
        profile_body.index("{servicios}")
        < profile_body.index("{unidades}")
        < profile_body.index("{tech}")
        < profile_body.index("{equipo}")
        < profile_body.index("{sedes}"),
        "public clinic ficha should keep medical content before location/access",
    )
    nav_body = source[source.index("def profile_nav("):source.index("def ficha(c):")]
    check(
        nav_body.index('profile_nav_item("Servicios", "#servicios")')
        < nav_body.index('profile_nav_item("Unidades", "#unidades")')
        < nav_body.index('profile_nav_item("Sedes", "#sedes")'),
        "profile navigation should list Sedes after medical sections",
    )

    print("OK public profile UX: navigation and richer search wired")


if __name__ == "__main__":
    main()
