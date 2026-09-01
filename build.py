# -*- coding: utf-8 -*-
"""Generador estático de Vitalarga — la guía de las clínicas de longevidad.
Uso: python3 build.py  ->  genera el sitio en dist/
Datos en data/clinics.json. Las fichas en pendientes/ NO se publican.
"""
import html, json, os, shutil, unicodedata, urllib.error, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
SITE = "Vitalarga"
TAGLINE = "La guía de las clínicas de longevidad"
BASE = "https://www.vitalarga.com"
LEGAL_OWNER = {
    "name": "Neurotrans SLU",
    "tax_id": "B-67221093",
    "address_line_1": "Padilla 327 Ent 68",
    "postal_city": "08025 Barcelona",
    "email": "admin@neurotrans.es",
}
PUBLIC_ENV_DEFAULTS = {
    "SUPABASE_URL": "https://twxhcmvzbpnrneywdece.supabase.co",
    "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_IHIMbYQacziyL1GcU6Mdtw_7AQdaCWg",
}
CITY_HINTS = (
    "Alicante",
    "Altea",
    "Barcelona",
    "Cofrentes",
    "L'Albir",
    "Madrid",
    "Málaga",
    "Malaga",
    "Mallorca",
    "Marbella",
    "Sevilla",
    "Valencia",
    "Zaragoza",
)

import re

def load_env_file():
    values = {}
    path = os.path.join(ROOT, ".env")
    if not os.path.exists(path):
        return values
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip("\"'")
    return values

LOCAL_ENV = load_env_file()

def public_env(key):
    return os.environ.get(key) or LOCAL_ENV.get(key) or PUBLIC_ENV_DEFAULTS.get(key, "")

def env_value(key, default=""):
    return os.environ.get(key) or LOCAL_ENV.get(key) or default

def load_clinics_from_json():
    with open(os.path.join(ROOT, "data", "clinics.json"), encoding="utf-8") as f:
        return json.load(f)

def load_clinics_from_supabase():
    url = public_env("SUPABASE_URL")
    key = public_env("SUPABASE_PUBLISHABLE_KEY")
    if not url or not key:
        raise RuntimeError("missing Supabase public config")

    request = urllib.request.Request(
        url.rstrip("/") + "/rest/v1/rpc/public_clinics_for_site",
        data=b"{}",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        clinics = json.loads(response.read().decode("utf-8"))
    if not isinstance(clinics, list):
        raise RuntimeError("Supabase clinic feed did not return a list")
    return clinics

def load_clinics():
    source = env_value("VITALARGA_DATA_SOURCE", "json").strip().lower()
    if source in ("supabase", "auto"):
        try:
            clinics = load_clinics_from_supabase()
            print(f"OK source: Supabase ({len(clinics)} clinics)")
            return clinics
        except (OSError, RuntimeError, urllib.error.URLError, json.JSONDecodeError) as exc:
            if source == "supabase":
                raise
            print(f"WARN source: Supabase unavailable, using data/clinics.json ({exc})")
    return load_clinics_from_json()

def normalize_clinic(clinic):
    clinic = dict(clinic)
    clinic.pop("internal_contact", None)
    for key in ("slug", "name", "city", "country", "address", "web", "summary", "status"):
        clinic[key] = clinic.get(key) or ""
    for key in (
        "tech",
        "email",
        "telefono",
        "phone_fixed",
        "phone_mobile",
        "phone_whatsapp",
        "instagram",
        "care_mode",
        "maps_url",
        "google_maps_url",
        "google_reviews_url",
        "reviews_url",
        "years_in_practice",
        "team_credentialing_visible",
        "public_pricing",
        "pricing_url",
    ):
        if key in clinic and clinic[key] is None:
            clinic[key] = ""
    for key in ("services", "specialties", "cities_extra", "profesionales", "unidades", "locations"):
        if not isinstance(clinic.get(key), list):
            clinic[key] = []
    return clinic

def sort_clinics(clinics):
    fallback_order = {
        clinic.get("slug"): index
        for index, clinic in enumerate(load_clinics_from_json())
        if clinic.get("slug")
    }
    return sorted(
        clinics,
        key=lambda clinic: (
            fallback_order.get(clinic.get("slug"), len(fallback_order) + 1),
            clinic.get("name", ""),
        ),
    )

def md_to_html(md):
    """Conversor markdown mínimo (sin dependencias, corre en Netlify build)."""
    out, paras = [], re.split(r"\n\s*\n", md.strip())
    for p in paras:
        p = p.strip()
        if p.startswith("## "):
            out.append(f"<h2>{p[3:].strip()}</h2>"); continue
        p = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", p)
        p = re.sub(r"\*(.+?)\*", r"<em>\1</em>", p)
        p = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', p)
        out.append(f"<p>{p}</p>")
    return "\n".join(out)

def load_posts():
    posts = []
    pdir = os.path.join(ROOT, "data", "posts")
    if not os.path.isdir(pdir):
        return posts
    for fn in sorted(os.listdir(pdir)):
        if not fn.endswith(".md"):
            continue
        raw = open(os.path.join(pdir, fn), encoding="utf-8").read()
        head, _, body = raw.partition("\n\n")
        meta = dict(l.split(":", 1) for l in head.strip().splitlines() if ":" in l)
        posts.append({
            "slug": fn[:-3],
            "title": meta.get("title", fn).strip(),
            "date": meta.get("date", "").strip(),
            "desc": meta.get("desc", "").strip(),
            "html": md_to_html(body),
        })
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts

def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return s.lower().replace(" ", "-")

def h(value):
    return html.escape(str(value or ""), quote=True)

def visible_values(values):
    return [str(value).strip() for value in values if str(value or "").strip()]

def external_url(value):
    value = str(value or "").strip()
    if value.startswith(("https://", "http://")):
        return value
    return ""

def first_text(*values):
    for value in values:
        clean = str(value or "").strip()
        if clean:
            return clean
    return ""

def positive_int(value):
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)) and int(value) > 0:
        return int(value)
    match = re.search(r"\d+", str(value or ""))
    return int(match.group(0)) if match else 0

def is_google_maps_profile_url(value):
    clean = urllib.parse.unquote_plus(str(value or "").strip()).lower()
    if not clean:
        return False
    if not (
        ("google." in clean and "/maps" in clean)
        or "maps.app.goo.gl" in clean
        or "goo.gl/maps" in clean
        or "g.page/" in clean
    ):
        return False
    if any(marker in clean for marker in ("/maps/search", "/maps/dir", "google.com/search")):
        return False
    has_profile_signal = any(marker in clean for marker in (
        "/maps/place/",
        "place_id:",
        "placeid=",
        "place_id=",
        "query_place_id=",
        "cid=",
        "ftid=",
        "maps.app.goo.gl",
        "goo.gl/maps",
        "g.page/",
    ))
    if not has_profile_signal:
        return False
    return not re.search(
        r"/maps/place/(calle|c/|avenida|av\.|avda\.?|paseo|passeig|plaza|ronda|carretera|road|street|carrer|camino|via)([\s,./-]|$)",
        clean,
    )

def location_from_dict(value):
    loc = {
        "name": first_text(value.get("name"), value.get("label"), value.get("sede")),
        "city": first_text(value.get("city"), value.get("ciudad")),
        "address": first_text(value.get("address"), value.get("direccion"), value.get("dirección")),
        "maps_url": external_url(first_text(value.get("maps_url"), value.get("google_maps_url"), value.get("map_url"))),
        "google_reviews_url": external_url(first_text(value.get("google_reviews_url"), value.get("reviews_url"), value.get("valoraciones_url"))),
        "kind": location_kind_value(value),
        "public_visible": location_public_visible_value(value),
    }
    has_content = any(loc.get(key) for key in ("name", "city", "address", "maps_url", "google_reviews_url")) or loc["kind"] == "online"
    return {key: item for key, item in loc.items() if item or key == "public_visible"} if has_content else {}

def location_from_text(value):
    clean = str(value or "").strip()
    if not clean:
        return {}
    if "|" not in clean:
        return {"address": clean}
    parts = [part.strip() for part in clean.split("|")]
    while len(parts) < 7:
        parts.append("")
    legacy_visibility = bool(parts[5]) and not is_location_kind(parts[5])
    loc = {
        "name": parts[0],
        "city": parts[1],
        "address": parts[2],
        "maps_url": external_url(parts[3]),
        "google_reviews_url": external_url(parts[4]),
        "kind": "" if legacy_visibility else location_kind_value(parts[5]),
        "public_visible": location_public_visible_value(parts[5] if legacy_visibility else parts[6]),
    }
    if not loc["address"] and parts[1] and len([part for part in parts if part]) == 2:
        loc["city"] = ""
        loc["address"] = parts[1]
    return {key: item for key, item in loc.items() if item or key == "public_visible"}

def city_from_address(address, fallback=""):
    clean = str(address or "")
    for city in CITY_HINTS:
        if re.search(r"\b" + re.escape(city) + r"\b", clean, flags=re.I):
            return city
    return str(fallback or "").strip()

def location_public_visible_value(value):
    if isinstance(value, dict):
        for key in ("public_visible", "online", "visible", "is_public"):
            if key in value:
                return location_public_visible_value(value.get(key))
        return True
    if isinstance(value, bool):
        return value
    clean = str(value or "").strip().lower()
    if clean in {"false", "0", "no", "offline", "hidden", "oculta", "oculto", "no online", "private"}:
        return False
    return True

def is_location_kind(value):
    clean = str(value or "").strip().lower()
    return clean in {"physical", "fisica", "física", "presencial", "online", "virtual", "remota"}

def location_kind_value(value):
    if isinstance(value, dict):
        for key in ("kind", "type", "tipo", "location_type"):
            if key in value:
                return location_kind_value(value.get(key))
        return "physical"
    clean = str(value or "").strip().lower()
    if clean in {"online", "virtual", "remota"}:
        return "online"
    return "physical"

def location_is_online(loc):
    return location_kind_value(loc) == "online"

def location_is_public(loc):
    return location_public_visible_value(loc)

def unique_locations(locations):
    seen = {}
    order = []
    for loc in locations:
        key_parts = [str(loc.get(name, "")).lower() for name in ("name", "city", "address", "maps_url", "kind")]
        key = "|".join(key_parts).strip("|")
        if not key:
            continue
        if key not in seen:
            seen[key] = loc
            order.append(key)
        elif not location_is_public(seen[key]) and location_is_public(loc):
            seen[key] = loc
    return [seen[key] for key in order]

def explicit_clinic_locations(c):
    locations = []
    raw = c.get("locations")
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                loc = location_from_dict(item)
            else:
                loc = location_from_text(item)
            if loc:
                locations.append(loc)
    elif isinstance(raw, str):
        for line in raw.splitlines():
            loc = location_from_text(line)
            if loc:
                locations.append(loc)
    return unique_locations(locations)

def clinic_locations(c):
    locations = explicit_clinic_locations(c)
    if locations:
        return [loc for loc in locations if location_is_public(loc)]
    address = str(c.get("address") or "").strip()
    if not address:
        return []
    parts = [part.strip() for part in address.split(" · ") if part.strip()]
    if len(parts) > 1:
        return [
            {"city": city_from_address(part, c.get("city", "")), "address": part}
            for part in parts
        ]
    return [{"city": city_from_address(address, c.get("city", "")), "address": address}]

def primary_location(c):
    locations = clinic_locations(c)
    if locations:
        return locations[0]
    return {}

def location_address(loc):
    return first_text(loc.get("address"), loc.get("direccion"), loc.get("dirección"))

def location_city(loc, c):
    return first_text(loc.get("city"), c.get("city"))

def location_display_name(loc, c, multiple=False):
    name = first_text(loc.get("name"), loc.get("label"), loc.get("sede"))
    if name and not re.match(r"^sede( principal|\s+\d+|\s+en\s+.+)?$", name, flags=re.I):
        return name
    if location_is_online(loc):
        return "Sede online"
    city = location_city(loc, c)
    if multiple and city:
        return f"Sede en {city}"
    return "Sede principal" if not multiple else "Sede"

def location_maps_url(loc, c):
    if location_is_online(loc):
        return ""
    direct = external_url(first_text(
        loc.get("maps_url"),
        loc.get("google_maps_url"),
        c.get("maps_url"),
        c.get("google_maps_url"),
    ))
    return direct if is_google_maps_profile_url(direct) else ""

def location_reviews_url(loc, c):
    if location_is_online(loc):
        return ""
    return external_url(first_text(
        loc.get("google_reviews_url"),
        loc.get("reviews_url"),
        c.get("google_reviews_url"),
        c.get("reviews_url"),
    ))

def location_detail(loc, c):
    if location_is_online(loc):
        city = location_city(loc, c)
        return f"Atención online · {city}" if city else "Atención online"
    address = location_address(loc)
    city = location_city(loc, c)
    if not address:
        return city
    if city and city.lower() not in address.lower():
        return f"{city} · {address}"
    return address

def care_mode_label(value):
    clean = str(value or "").strip().lower()
    labels = {
        "presencial": "Presencial",
        "online": "Online",
        "hibrida": "Presencial y online",
        "hybrid": "Presencial y online",
        "mixta": "Presencial y online",
        "no_consta": "No consta",
    }
    return labels.get(clean, str(value or "").strip())

def transparency_status_label(value):
    clean = str(value or "").strip()
    lower = clean.lower()
    if lower in {"yes", "true", "1", "si", "sí", "publico", "público", "visible"}:
        return "Sí"
    if lower in {"partial", "parcial", "parte"}:
        return "Parcial"
    if lower in {"no", "false", "0"}:
        return "No publicado"
    if lower in {"unknown", "no consta", "sin dato"}:
        return "No consta"
    return clean

def transparency_items(c):
    items = []
    years = first_text(c.get("years_in_practice"), c.get("years_active"), c.get("founded_year"))
    if years:
        items.append(("Años en ejercicio", h(years)))
    specialists = first_text(c.get("specialists_count"), c.get("num_specialists"), c.get("specialists_public_count"))
    if specialists:
        items.append(("Número de especialistas", h(specialists)))
    credentialing = transparency_status_label(first_text(
        c.get("team_credentialing_visible"),
        c.get("medical_license_visible"),
        c.get("colegiacion_visible"),
    ))
    if credentialing:
        items.append(("Colegiación visible", h(credentialing)))
    pricing = transparency_status_label(first_text(c.get("public_pricing"), c.get("prices_public"), c.get("price_public")))
    pricing_url = external_url(c.get("pricing_url"))
    if pricing:
        if pricing_url:
            pricing = f'<a href="{h(pricing_url)}" rel="nofollow noopener" target="_blank">{h(pricing)}</a>'
        else:
            pricing = h(pricing)
        items.append(("Precio público", pricing))
    return items

def display_url(value):
    value = str(value or "").strip()
    return value.replace("https://", "").replace("http://", "").rstrip("/")

def instagram_parts(value):
    raw = str(value or "").strip()
    if not raw:
        return "", ""
    if raw.startswith(("https://", "http://")):
        handle = "@" + raw.rstrip("/").rsplit("/", 1)[-1].lstrip("@")
        return handle, raw
    handle = raw if raw.startswith("@") else "@" + raw
    return handle, f"https://www.instagram.com/{handle.lstrip('@').strip('/')}/"

def split_text_list(value):
    if isinstance(value, list):
        return visible_values(value)
    text = str(value or "").strip()
    if not text:
        return []
    for sep in ("\n", ";"):
        text = text.replace(sep, ",")
    return visible_values(text.split(","))

def phone_href(value, whatsapp=False):
    digits = re.sub(r"[^0-9+]", "", str(value or ""))
    if not digits:
        return ""
    if whatsapp:
        return "https://wa.me/" + re.sub(r"\D", "", digits)
    return "tel:" + digits

def phone_search_value(value):
    clean = str(value or "").strip()
    digits = re.sub(r"\D", "", clean)
    return " ".join(part for part in (clean, digits) if part)

def add_contact_phone(items, seen, label, value, whatsapp=False):
    clean = str(value or "").strip()
    if not clean:
        return
    key = re.sub(r"\D", "", clean) or clean.lower()
    if key in seen:
        return
    seen.add(key)
    href = phone_href(clean, whatsapp)
    items.append((label, clean, href))

def contact_phone_items(c):
    items = []
    seen = set()
    raw_phones = c.get("phones")
    if isinstance(raw_phones, list):
        for item in raw_phones:
            if isinstance(item, dict):
                label = first_text(item.get("label"), item.get("type"), item.get("tipo"), "Teléfono")
                value = first_text(item.get("value"), item.get("phone"), item.get("telefono"), item.get("number"), item.get("numero"))
                whatsapp = "whatsapp" in label.lower() or str(item.get("whatsapp") or "").lower() in {"true", "1", "si", "sí"}
                add_contact_phone(items, seen, label, value, whatsapp)
            else:
                add_contact_phone(items, seen, "Teléfono", item)
    add_contact_phone(items, seen, "Teléfono", c.get("telefono"))
    add_contact_phone(items, seen, "Fijo", c.get("phone_fixed"))
    add_contact_phone(items, seen, "Móvil", c.get("phone_mobile"))
    add_contact_phone(items, seen, "WhatsApp", c.get("phone_whatsapp"), True)
    return items

def contact_count(c):
    count = len(contact_phone_items(c))
    count += 1 if str(c.get("email") or "").strip() else 0
    count += 1 if str(c.get("instagram") or "").strip() else 0
    return count

def stat_items(c):
    locations_count = len(clinic_locations(c))
    services_count = len(visible_values(c.get("services")))
    specialties_count = len(visible_values(c.get("specialties")))
    units_count = len(visible_values(c.get("unidades")))
    specialists_count = max(len(visible_values(c.get("profesionales"))), positive_int(c.get("specialists_count")))
    tech_count = len(split_text_list(c.get("tech")))
    contacts = contact_count(c)
    items = []
    if locations_count > 1:
        items.append(("Sedes", locations_count))
    if services_count:
        items.append(("Servicios", services_count))
    if specialties_count:
        items.append(("Especialidades", specialties_count))
    if units_count:
        items.append(("Unidades", units_count))
    if specialists_count:
        items.append(("Especialistas", specialists_count))
    if tech_count:
        items.append(("Tecnología", tech_count))
    if contacts:
        items.append(("Contacto", contacts))
    return items

clinics = [normalize_clinic(c) for c in load_clinics()]
clinics = [c for c in clinics if c.get("status") in ("publicada", "preliminar")]
clinics = sort_clinics(clinics)

# logos aprobados (descargados por GitHub Actions en assets/logos/)
# Homogeneidad: en tarjetas se usa la MINIATURA normalizada (thumb, <=260x64) dentro
# de una pastilla blanca de altura fija; en la ficha, el logo original.
LOGOS_FILE = os.path.join(ROOT, "data", "logos.json")
ORIG_DIR = os.path.join(ROOT, "assets", "logos", "orig")
THUMB_DIR = os.path.join(ROOT, "assets", "logos", "thumb")

def _looks_like_logo_asset(path):
    try:
        with open(path, "rb") as f:
            head = f.read(512).lstrip().lower()
    except OSError:
        return False
    if not head:
        return False
    if head.startswith((b"<!doctype", b"<html")) or b"<meta http-equiv" in head[:300]:
        return False
    if os.path.splitext(path)[1].lower() == ".svg" and b"<svg" not in head:
        return False
    return True

def _find(dirpath, slug):
    if not os.path.isdir(dirpath):
        return None
    for fn in os.listdir(dirpath):
        if os.path.splitext(fn)[0] == slug and _looks_like_logo_asset(os.path.join(dirpath, fn)):
            return fn
    return None

logo_files, thumb_files = {}, {}
if os.path.exists(LOGOS_FILE):
    _logos = json.load(open(LOGOS_FILE, encoding="utf-8"))
    for _slug, _info in _logos.items():
        if not _info.get("aprobado"):
            continue
        _o, _t = _find(ORIG_DIR, _slug), _find(THUMB_DIR, _slug)
        if _o: logo_files[_slug] = _o
        if _t: thumb_files[_slug] = _t

cities = {}
for c in clinics:
    cities.setdefault(c["city"], []).append(c)
city_order = sorted(cities.keys(), key=lambda k: (-len(cities[k]), k))
countries = sorted({c["country"] for c in clinics})
specialties = sorted({s for c in clinics for s in c["specialties"]})

CSS = """
:root{--bg:#EFEBE2;--surface:#F7F4EE;--surface-strong:#fff;--ink:#12211F;--muted:#5A6764;--green:#0E4F4A;--green-deep:#0B3E3A;--green-mid:#16645C;--coral:#C9A15A;--line:#DED8CB;--line-strong:#C7DBD5;--wash:#DCEAE6;--soft:#F6EBD4;--shadow:0 18px 44px rgba(18,33,31,.08)}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{font-family:'Archivo',system-ui,sans-serif;background:var(--bg);color:var(--ink);line-height:1.58;-webkit-font-smoothing:antialiased}
a{color:var(--green-deep);text-decoration:none}a:hover{text-decoration:underline;text-underline-offset:3px}
.site{position:sticky;top:0;z-index:10;padding:.95rem 5vw;display:flex;justify-content:space-between;align-items:center;gap:1rem;border-bottom:1px solid var(--line);background:rgba(247,244,238,.92);backdrop-filter:blur(14px)}
.site .logo{display:inline-flex;align-items:center;gap:.68rem;font-family:'Newsreader',Georgia,serif;font-size:1.55rem;font-weight:400;color:var(--ink);letter-spacing:.01em}
.site .logo:hover{text-decoration:none;color:var(--green)}
.logo-mark{display:inline-block;width:30px;height:30px;border-radius:50%;border:1.4px solid var(--coral);position:relative;flex:0 0 auto}
.logo-mark::after{content:"";position:absolute;inset:7px;border-radius:50%;background:var(--coral)}
.site nav{display:flex;align-items:center;gap:.35rem;flex-wrap:wrap;justify-content:flex-end}
.site nav a{padding:.42rem .7rem;border-radius:8px;color:var(--muted);font-weight:700;font-size:.95rem}
.site nav a:hover{background:var(--wash);color:var(--green-deep);text-decoration:none}
.hero{max-width:1180px;margin:0 auto;padding:2.35rem 5vw 1rem}
.hero-copy{max-width:860px}
.hero .kicker{color:var(--coral);font-size:.82rem;font-weight:800;text-transform:uppercase;letter-spacing:0}
.hero h1{max-width:24ch;margin:.55rem 0 0;font-family:'Newsreader',Georgia,serif;font-size:3.2rem;font-weight:300;line-height:1.05;text-wrap:balance}
.hero h1 em{color:var(--green);font-style:italic}
.hero p.sub{max-width:660px;margin:1rem 0 0;color:var(--muted);font-size:1.18rem}
.finder{margin-top:1.35rem;background:var(--surface-strong);border:1px solid var(--line);border-radius:8px;padding:.9rem;box-shadow:var(--shadow)}
.finder input{width:100%;min-height:3.35rem;font:inherit;font-size:1.04rem;padding:.75rem 1rem;border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--ink)}
.finder input:focus{outline:3px solid rgba(14,79,74,.22);border-color:var(--green)}
.filter-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.75rem;margin-top:.85rem}
.fgroup{min-width:0}
.fgroup .flabel{display:block;margin-bottom:.35rem;color:var(--muted);font-size:.72rem;font-weight:800;text-transform:uppercase;letter-spacing:0}
.chips{display:flex;flex-wrap:nowrap;gap:.38rem;overflow-x:auto;padding-bottom:.08rem;scrollbar-width:thin}
.chip{font:inherit;font-size:.84rem;line-height:1.2;min-height:2.1rem;padding:.34rem .62rem;border-radius:8px;border:1px solid var(--line);background:#fff;color:var(--ink);cursor:pointer;white-space:nowrap}
.chip:hover{border-color:var(--green);color:var(--green-deep)}
.chip.on{background:var(--green);border-color:var(--green);color:#fff}
.logo-carousel{display:grid;grid-template-columns:42px minmax(0,1fr) 42px;align-items:center;gap:.45rem;max-width:1180px;margin:.25rem auto 0;padding:.5rem 5vw 1.05rem;box-sizing:border-box}
.logo-viewport{min-width:0;position:relative;overflow:hidden;-webkit-mask-image:linear-gradient(90deg,transparent,#000 22px,#000 calc(100% - 22px),transparent);mask-image:linear-gradient(90deg,transparent,#000 22px,#000 calc(100% - 22px),transparent)}
.logo-strip{min-width:0;display:flex;gap:.6rem;overflow-x:auto;margin:0;padding:.1rem;scroll-behavior:smooth;scroll-snap-type:x mandatory;scrollbar-width:none;overscroll-behavior-x:contain}
.logo-strip::-webkit-scrollbar{display:none}
.logo-nav{width:42px;height:42px;display:inline-grid;place-items:center;border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--green-deep);font:inherit;font-size:1.45rem;font-weight:800;line-height:1;cursor:pointer}
.logo-nav:hover{border-color:#C7DBD5;background:var(--surface-strong)}
.logo-nav:focus-visible{outline:3px solid rgba(14,79,74,.25);outline-offset:3px}
.logo-nav:disabled{opacity:.35;cursor:not-allowed}
.mini-logo{flex:0 0 auto;height:42px;display:flex;align-items:center;padding:.35rem .7rem;border:1px solid var(--line);border-radius:8px;background:rgba(247,244,238,.82)}
.mini-logo:hover{text-decoration:none;background:#fff;border-color:#C7DBD5}
.mini-logo:focus-visible{outline:3px solid rgba(14,79,74,.25);outline-offset:3px}
.mini-logo{scroll-snap-align:center}
.mini-logo.logo-clone{scroll-snap-align:none}
.logo-carousel .mini-logo.logo-failed{display:none}
.mini-logo img{max-width:126px;max-height:26px;object-fit:contain;display:block}
.logo-fallback{display:none;color:var(--green-deep);font-size:.82rem;font-weight:800;line-height:1.1;overflow-wrap:anywhere}
.logo-failed img{display:none}
.logo-failed .logo-fallback{display:block}
.results-section{max-width:1180px;margin:0 auto;padding:0 5vw 4rem}
.wrap{max-width:1180px;margin:0 auto;padding:0 5vw 4rem}
.resbar{position:sticky;top:66px;z-index:5;display:flex;align-items:center;justify-content:space-between;gap:.9rem;margin:.5rem 0 1rem;padding:.72rem .85rem;border:1px solid var(--line);border-radius:8px;background:rgba(247,244,238,.94);backdrop-filter:blur(12px)}
.rescount{color:var(--muted);font-size:.96rem}
.rescount b{color:var(--ink)}
.clear-btn{font:inherit;border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--green-deep);padding:.4rem .7rem;font-weight:800;cursor:pointer}
.clear-btn:disabled{cursor:not-allowed;opacity:.45}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(295px,1fr));gap:1rem}
.card{position:relative;display:flex;flex-direction:column;min-height:365px;padding:1rem;border:1px solid var(--line);border-radius:8px;background:var(--surface);box-shadow:0 1px 0 rgba(23,35,31,.03);transition:transform .15s ease,box-shadow .15s ease,border-color .15s ease}
.card:hover{transform:translateY(-2px);border-color:#C7DBD5;box-shadow:var(--shadow)}
.card-head{display:flex;align-items:flex-start;justify-content:space-between;gap:.7rem;min-height:48px}
.card .loc{display:block;margin-top:.35rem;color:var(--coral);font-size:.78rem;font-weight:800;text-transform:uppercase;letter-spacing:0}
.card h3{margin-top:.25rem;font-family:'Newsreader',Georgia,serif;font-size:1.28rem;font-weight:500;line-height:1.12}
.card h3 a{color:var(--ink)}
.card p{margin-top:.6rem;color:var(--muted);font-size:.96rem;flex:1}
.card-signals{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.45rem;margin-top:.85rem}
.card-signals div{min-width:0;border:1px solid var(--line);border-radius:8px;background:#fff;padding:.45rem .55rem}
.card-signals dt{color:var(--muted);font-size:.68rem;font-weight:800;text-transform:uppercase;letter-spacing:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.card-signals dd{margin:.12rem 0 0;color:var(--green-deep);font-size:1rem;font-weight:800;line-height:1}
.tags{display:flex;flex-wrap:wrap;gap:.35rem;margin-top:.8rem}
.tag{display:inline-flex;align-items:center;min-height:1.55rem;font-size:.78rem;padding:.18rem .55rem;border-radius:8px;background:var(--wash);color:var(--green-deep)}
.badge{display:inline-flex;align-items:center;min-height:1.45rem;font-size:.72rem;padding:.18rem .5rem;border-radius:8px;background:var(--soft);color:var(--muted);font-weight:800;white-space:nowrap}
.card-cta{align-self:flex-start;margin-top:1rem;padding:.48rem .75rem;border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--green-deep);font-weight:800}
.card-cta:hover{background:var(--wash);text-decoration:none}
.logo-link{display:inline-flex;align-self:flex-start;border-radius:8px}
.logo-link:hover{text-decoration:none}
.logo-link:focus-visible{outline:3px solid rgba(14,79,74,.25);outline-offset:3px}
.logobox{height:44px;width:fit-content;max-width:190px;display:flex;align-items:center;background:#fff;border:1px solid var(--line);border-radius:8px;padding:.35rem .65rem;align-self:flex-start}
.logobox img{max-height:29px;max-width:160px;object-fit:contain;display:block}
.logobox .logo-fallback{max-width:160px}
.flogo{height:62px;max-width:255px;margin-bottom:1rem}
.flogo img{max-height:43px;max-width:225px}
.flogo .logo-fallback{max-width:225px;font-size:1rem}
.hidden{display:none!important}
.empty-state{padding:2rem;border:1px dashed var(--line-strong);border-radius:8px;background:rgba(247,244,238,.72);color:var(--muted);text-align:center}
.ficha{max-width:1120px;margin:0 auto;padding:2.1rem 5vw 4rem}
.crumbs{font-size:.9rem;color:var(--muted);margin-bottom:1.25rem}
.clinic-intro{display:grid;grid-template-columns:minmax(0,1fr) 330px;gap:2rem;align-items:start}
.clinic-main{min-width:0}
.clinic-main h1,.ficha>h1{font-family:'Newsreader',Georgia,serif;font-size:3.05rem;font-weight:300;line-height:1.04;text-wrap:balance}
.ficha .loc{color:var(--coral);text-transform:uppercase;font-size:.86rem;font-weight:800;margin:.6rem 0 1rem;letter-spacing:0;overflow-wrap:anywhere}
.ficha .summary{max-width:720px;margin-top:1rem;font-size:1.18rem;color:var(--ink)}
.profile-jump{display:grid;gap:.45rem;margin-top:1rem}
.profile-jump-label{color:var(--muted);font-size:.74rem;font-weight:800;text-transform:uppercase;letter-spacing:0}
.profile-nav{display:flex;flex-wrap:wrap;gap:.45rem}
.profile-nav a{display:inline-flex;align-items:center;min-height:1.85rem;padding:.32rem .62rem;border:1px solid var(--line);border-radius:8px;background:var(--surface);color:var(--green-deep);font-size:.84rem;font-weight:800}
.profile-nav a:hover{background:var(--wash);text-decoration:none}
.clinic-side{display:grid;gap:1rem;padding:1rem;border:1px solid var(--line);border-radius:8px;background:var(--surface);box-shadow:0 1px 0 rgba(23,35,31,.03)}
.clinic-side .profile-block{margin-top:0;padding:0;border:0;border-radius:0;background:transparent;box-shadow:none}
.clinic-side h2{margin-top:0}
.profile-sections{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem;margin-top:1.5rem;align-items:start}
.profile-block{min-width:0;padding:1.05rem 1.1rem;border:1px solid var(--line);border-radius:8px;background:var(--surface);box-shadow:0 1px 0 rgba(23,35,31,.03)}
.profile-section-head{display:flex;align-items:center;justify-content:space-between;gap:.75rem;margin-bottom:.6rem}
.ficha h2{font-family:'Newsreader',Georgia,serif;font-weight:500;font-size:1.22rem;margin:0}
.ficha ul{padding-left:1.1rem;color:var(--muted)}
.profile-block li{margin:.24rem 0}
.profile-list{list-style:none;padding-left:0!important;display:grid;gap:.52rem;color:var(--muted)}
.profile-list li{position:relative;margin:0!important;padding-left:1rem;line-height:1.45}
.profile-list li::before{content:"";position:absolute;left:0;top:.62em;width:.38rem;height:.38rem;border-radius:8px;background:var(--coral)}
.facts{display:grid;grid-template-columns:1fr;gap:.75rem;margin:.75rem 0 0}
.facts div{border-top:1px solid var(--line);padding-top:.55rem}
.facts dt{font-size:.74rem;text-transform:uppercase;color:var(--coral);font-weight:800;letter-spacing:0}
.facts dd{margin:0;color:var(--ink);overflow-wrap:anywhere}
.info-list{display:grid;gap:.38rem}
.location-list{display:grid;gap:.72rem}
.profile-location-block{grid-column:1/-1;align-self:start}
.profile-location-multiple{grid-column:1/-1}
.profile-location-multiple .location-list{grid-template-columns:repeat(auto-fit,minmax(15rem,1fr));gap:.75rem}
.profile-location-multiple .location-item{border:1px solid var(--line);border-radius:8px;padding:.85rem;background:#fff}
.profile-location-multiple .location-item:first-child{border-top:1px solid var(--line);padding-top:.85rem}
.location-item{border-top:1px solid var(--line);padding-top:.72rem}
.location-item:first-child{border-top:0;padding-top:0}
.location-item h3{font-family:'Archivo',system-ui,sans-serif;font-size:1rem;line-height:1.2;margin:0 0 .15rem;font-weight:800;color:var(--ink)}
.location-item p{color:var(--muted);margin:.15rem 0 .45rem;overflow-wrap:anywhere}
.location-actions{display:flex;flex-wrap:wrap;gap:.45rem}
.mini-action{display:inline-flex;align-items:center;justify-content:center;min-height:1.9rem;padding:.3rem .58rem;border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--green-deep);font-size:.84rem;font-weight:800}
.mini-action:hover{background:var(--wash);text-decoration:none}
.transparency-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.55rem}
.transparency-grid div{min-width:0;border-top:1px solid var(--line);padding-top:.55rem}
.transparency-grid dt{font-size:.72rem;text-transform:uppercase;color:var(--coral);font-weight:800;letter-spacing:0}
.transparency-grid dd{margin:0;color:var(--ink);overflow-wrap:anywhere}
.pill-list{display:flex;flex-wrap:wrap;gap:.45rem;list-style:none;padding-left:0!important}
.pill-list li{font-size:.86rem;padding:.3rem .62rem;border-radius:8px;background:var(--wash);color:var(--green-deep)}
.contacto{list-style:none;padding-left:0!important}
.contacto li{margin:.25rem 0;overflow-wrap:anywhere}
.contacto b{color:var(--ink);font-weight:700}
.muted-copy{color:var(--muted)}
.visit{display:inline-flex;justify-content:center;align-items:center;margin-top:.25rem;background:var(--green);color:#fff;padding:.68rem 1rem;border-radius:8px;font-weight:800;text-align:center}
.visit:hover{text-decoration:none;background:var(--green-deep)}
.clinic-side .visit{width:100%}
.note{background:var(--soft);border:1px solid var(--line);border-radius:8px;padding:1rem 1.1rem;font-size:.93rem;color:var(--muted);margin-top:1.4rem}
.order-note{margin:.2rem 0 1rem;color:var(--muted);font-size:.92rem;font-weight:700}
.recommend{max-width:1180px;margin:.25rem auto 1rem;padding:0 5vw}
.recommend-inner{display:grid;gap:.75rem;padding:1rem;border:1px solid var(--line);border-radius:8px;background:var(--surface);box-shadow:0 1px 0 rgba(23,35,31,.03)}
.recommend-head{display:flex;align-items:center;justify-content:space-between;gap:1rem}
.recommend-head h2{font-family:'Newsreader',Georgia,serif;font-weight:500;font-size:1.35rem;line-height:1.1}
.recommend-head p{margin:.25rem 0 0;color:var(--muted);max-width:58ch}
.recommend-toggle,.recommend-submit{font:inherit;display:inline-flex;align-items:center;justify-content:center;min-height:2.55rem;padding:.55rem .85rem;border:1px solid var(--green);border-radius:8px;background:var(--green);color:#fff;font-weight:800;cursor:pointer;white-space:nowrap}
.recommend-toggle:hover,.recommend-submit:hover{background:var(--green-deep);text-decoration:none}
.recommend-form{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.75rem;padding-top:.75rem;border-top:1px solid var(--line)}
.recommend-form label{display:block;margin-bottom:.28rem;color:var(--muted);font-size:.72rem;font-weight:800;text-transform:uppercase;letter-spacing:0}
.recommend-form input,.recommend-form select,.recommend-form textarea{width:100%;min-height:2.65rem;font:inherit;font-size:.96rem;padding:.58rem .72rem;border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--ink)}
.recommend-form textarea{min-height:5rem;resize:vertical}
.recommend-form input:focus,.recommend-form select:focus,.recommend-form textarea:focus{outline:3px solid rgba(14,79,74,.22);border-color:var(--green)}
.recommend-wide{grid-column:1/-1}
.recommend-actions{grid-column:1/-1;display:flex;align-items:center;justify-content:space-between;gap:.75rem;flex-wrap:wrap}
.recommend-status{margin:0;color:var(--muted);font-weight:700}
.recommend-status.ok{color:var(--green-deep)}
.recommend-status.error{color:#B63B2E}
.recommend-trap{position:absolute!important;left:-10000px!important;width:1px!important;height:1px!important;overflow:hidden!important}
footer{border-top:1px solid var(--line);padding:2rem 5vw;color:var(--muted);font-size:.9rem;background:rgba(247,244,238,.56)}
.footer-inner{max-width:1120px;margin:0 auto;display:grid;gap:.72rem}
footer p{margin:0}
.legal-id{font-size:.86rem}
.legal-links{display:flex;flex-wrap:wrap;gap:.7rem}
.legal-links a{color:var(--green-deep);font-weight:800}
.legal-copy{display:grid;gap:1rem;margin-top:1.2rem;color:var(--muted)}
.legal-copy h2{margin-top:.4rem}
@media(prefers-reduced-motion:reduce){.card{transition:none}.card:hover{transform:none}}
@media(max-width:860px){.hero{padding-top:2rem}.hero h1{font-size:2.65rem}.filter-grid,.profile-sections,.clinic-intro,.recommend-form{grid-template-columns:1fr}.clinic-side{order:2}.resbar{position:static;align-items:flex-start;flex-direction:column}.clear-btn{width:100%}.recommend-head{align-items:flex-start;flex-direction:column}.recommend-toggle{width:100%}}
@media(max-width:640px){.site{position:static;align-items:flex-start;flex-direction:column}.site nav{justify-content:flex-start}.hero h1{font-size:2.25rem}.hero p.sub,.ficha .summary{font-size:1.05rem}.finder{padding:.75rem}.logo-carousel{grid-template-columns:38px minmax(0,1fr) 38px}.logo-nav{width:38px;height:38px;font-size:1.3rem}.grid{grid-template-columns:1fr}.card{min-height:auto}.clinic-main h1,.ficha>h1{font-size:2.2rem}.facts,.transparency-grid{grid-template-columns:1fr}.profile-nav{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))}.profile-nav a{min-width:0;padding:.36rem .45rem}.profile-nav-label{min-width:0;overflow:hidden;text-overflow:ellipsis}.recommend-actions{display:grid;grid-template-columns:1fr}.recommend-submit{width:100%}}
"""

HEAD = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website"><meta property="og:site_name" content="Vitalarga">
<meta property="og:title" content="{title}"><meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}"><meta property="og:locale" content="es_ES">
<meta name="twitter:card" content="summary">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,300;0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,300;1,6..72,400&family=Archivo:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/style.css">
<script data-goatcounter="https://vitalarga.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
{jsonld}</head><body>
<header class="site"><a class="logo" href="/"><span class="logo-mark" aria-hidden="true"></span><span>Vitalarga</span></a>
<nav><a href="/#buscar">Buscar clínica</a><a href="/#recomendar-clinica">Recomendar Clínica</a><a href="/blog/">Blog</a><a href="/sobre/">Sobre la guía</a></nav></header>
"""

FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<rect width="64" height="64" rx="14" fill="#F7F4EE"/>
<circle cx="32" cy="32" r="19" fill="none" stroke="#C9A15A" stroke-width="3"/>
<circle cx="32" cy="32" r="9" fill="#0E4F4A"/>
</svg>
"""

def head(title, desc, path, jsonld=""):
    return HEAD.format(title=title, desc=desc, url=BASE + path, jsonld=jsonld)

def legal_owner_address():
    return f'{LEGAL_OWNER["address_line_1"]}, {LEGAL_OWNER["postal_city"]}'

def legal_owner_summary_html():
    email = LEGAL_OWNER["email"]
    return (
        '<p class="legal-id"><strong>Titular:</strong> '
        f'{h(LEGAL_OWNER["name"])} · NIF {h(LEGAL_OWNER["tax_id"])} · '
        f'{h(legal_owner_address())} · '
        f'<a href="mailto:{h(email)}">{h(email)}</a></p>'
    )

FOOTER = f"""<footer><div class="footer-inner"><p><strong>Vitalarga</strong> — {TAGLINE}. Guía informativa e independiente: no emitimos recomendaciones médicas, no hacemos rankings y ninguna clínica paga por aparecer. Cada ficha se elabora a partir de información pública y se revisa manualmente.</p>{legal_owner_summary_html()}<nav class="legal-links" aria-label="Información legal"><a href="/aviso-legal/">Aviso legal</a><a href="/privacidad/">Privacidad</a><a href="/cookies/">Cookies</a></nav></div></footer></body></html>"""

def attrs(c):
    extra = c.get("cities_extra", [])
    all_cities = "|".join([c["city"]] + extra)
    locations_text = " ".join(
        " ".join(visible_values([loc.get("name"), loc.get("city"), loc.get("address")]))
        for loc in clinic_locations(c)
    )
    phone_text = " ".join(
        " ".join(visible_values([label, value, phone_search_value(value)]))
        for label, value, _ in contact_phone_items(c)
    )
    transparency_text = " ".join(value for _, value in transparency_items(c) if "<a " not in str(value))
    search_parts = [
        c["name"],
        c["city"],
        c["country"],
        c.get("region", ""),
        c.get("address", ""),
        c.get("summary", ""),
        c.get("web", ""),
        c.get("tech", ""),
        c.get("email", ""),
        c.get("telefono", ""),
        c.get("phone_fixed", ""),
        c.get("phone_mobile", ""),
        c.get("phone_whatsapp", ""),
        c.get("instagram", ""),
        c.get("care_mode", ""),
        phone_text,
        locations_text,
        transparency_text,
        c.get("years_in_practice", ""),
        c.get("specialists_count", ""),
        c.get("team_credentialing_visible", ""),
        c.get("public_pricing", ""),
        " ".join(c["specialties"]),
        " ".join(c["services"]),
        " ".join(c.get("unidades", [])),
        " ".join(c.get("profesionales", [])),
    ]
    search_text = " ".join(str(part).lower() for part in search_parts if part)
    return f'data-slug="{h(c["slug"])}" data-city="{h(all_cities)}" data-country="{h(c["country"])}" data-spec="{h("|".join(c["specialties"]))}" data-text="{h(search_text)}"'

def logo_img(c, ficha=False):
    if ficha:
        fn = logo_files.get(c["slug"]) or thumb_files.get(c["slug"])
        sub = "orig"
    else:
        fn = thumb_files.get(c["slug"]) or logo_files.get(c["slug"])
        sub = "thumb"
    if not fn:
        return ""
    cls = "logobox flogo" if ficha else "logobox"
    return (
        f'<span class="{cls}"><img src="/assets/logos/{sub}/{h(fn)}" '
        f'alt="Logo de {h(c["name"])}" loading="lazy" onerror="this.closest(\'.logobox\').classList.add(\'logo-failed\')">'
        f'<span class="logo-fallback">{h(c["name"])}</span></span>'
    )

def card_logo(c):
    logo = logo_img(c)
    if not logo:
        return ""
    return f'<a class="logo-link" href="/clinica/{h(c["slug"])}/" aria-label="Ver ficha de {h(c["name"])}">{logo}</a>'

def card_signal_html(c):
    items = stat_items(c)
    if not items:
        return ""
    featured = []
    for label, count in items:
        if label != "Especialidades":
            featured.append((label, count))
    if len(featured) < 2:
        featured = items
    return '<dl class="card-signals" aria-label="Datos visibles de la ficha">' + "".join(
        f"<div><dt>{h(label)}</dt><dd>{h(count)}</dd></div>"
        for label, count in featured[:4]
    ) + "</dl>"

def card(c):
    badge = '<span class="badge">Preliminar</span>' if c["status"] == "preliminar" else ""
    extra = (" · " + " · ".join(c["cities_extra"])) if c.get("cities_extra") else ""
    tags = "".join(f'<span class="tag">{h(s)}</span>' for s in c["specialties"])
    summary = h(c["summary"][:150]) + ("…" if len(c["summary"]) > 150 else "")
    signals = card_signal_html(c)
    return f'''<article class="card" {attrs(c)}><div class="card-head">{card_logo(c)}{badge}</div>
<span class="loc">{h(c["city"])}{h(extra)} · {h(c["country"])}</span>
<h3><a href="/clinica/{h(c["slug"])}/">{h(c["name"])}</a></h3>
<p>{summary}</p>
{signals}
<div class="tags">{tags}</div><a class="card-cta" href="/clinica/{h(c["slug"])}/">Ver ficha</a></article>'''

# --- index ---
city_chips = "".join(f'<button class="chip" data-f="city" data-v="{h(ct)}">{h(ct)}</button>' for ct in city_order)
country_chips = "".join(f'<button class="chip" data-f="country" data-v="{h(co)}">{h(co)}</button>' for co in countries)
spec_chips = "".join(f'<button class="chip" data-f="spec" data-v="{h(s)}">{h(s)}</button>' for s in specialties)
allcards = "".join(card(c) for c in clinics)
featured_logo_clinics = [c for c in clinics if c.get("slug") in thumb_files]
featured_logos = "".join(
    f'<a class="mini-logo" href="/clinica/{h(c["slug"])}/" data-neutral-item data-slug="{h(c["slug"])}" aria-label="Ver ficha de {h(c["name"])}"><img src="/assets/logos/thumb/{h(thumb_files[c["slug"]])}" alt="{h(c["name"])}" loading="lazy" onerror="this.closest(\'.mini-logo\').classList.add(\'logo-failed\')"><span class="logo-fallback">{h(c["name"])}</span></a>'
    for c in featured_logo_clinics
)

PUBLIC_SITE_CONFIG_JSON = json.dumps({
    "supabaseUrl": public_env("SUPABASE_URL"),
    "supabasePublishableKey": public_env("SUPABASE_PUBLISHABLE_KEY"),
}, ensure_ascii=False).replace("<", "\\u003c")
PUBLIC_SITE_CONFIG = f'<script>window.VITALARGA_PUBLIC_CONFIG={PUBLIC_SITE_CONFIG_JSON};</script>'
ORDER_NOTE = '<p class="order-note">El orden de las fichas rota de forma neutra: no es un ranking ni una recomendación médica.</p>'

NEUTRAL_ORDER_JS = """<script>
(function(){
  function hashText(value){
    var hash=2166136261;
    value=String(value||"");
    for(var i=0;i<value.length;i++){
      hash^=value.charCodeAt(i);
      hash+=(hash<<1)+(hash<<4)+(hash<<7)+(hash<<8)+(hash<<24);
    }
    return hash>>>0;
  }
  function daySeed(){
    var now=new Date();
    var start=Date.UTC(now.getUTCFullYear(),0,1);
    var today=Date.UTC(now.getUTCFullYear(),now.getUTCMonth(),now.getUTCDate());
    return String(now.getUTCFullYear())+"-"+String(Math.floor((today-start)/86400000));
  }
  function itemSlug(item){
    return item.getAttribute("data-slug")||item.textContent||"";
  }
  function neutralOrderKey(item,scope,seed){
    return hashText(scope+"|"+seed+"|"+itemSlug(item));
  }
  window.applyNeutralCardOrder=function(){
    var seed=daySeed();
    document.querySelectorAll("[data-neutral-results]").forEach(function(container){
      var scope=container.getAttribute("data-neutral-results")||"public";
      var items=[].slice.call(container.children).filter(function(item){
        return item.matches&&item.matches(".card,[data-neutral-item]");
      });
      if(items.length<2) return;
      items.map(function(item,index){
        return {item:item,index:index,key:neutralOrderKey(item,scope,seed),slug:itemSlug(item)};
      }).sort(function(a,b){
        return (a.key-b.key)||a.slug.localeCompare(b.slug)||a.index-b.index;
      }).forEach(function(entry){
        container.appendChild(entry.item);
      });
    });
  };
  window.applyNeutralCardOrder();
})();
</script>"""

JS = """<script>
(function(){
  var state={city:null,country:null,spec:null,q:"",qDigits:""};
  var cards=[].slice.call(document.querySelectorAll(".grid .card"));
  var count=document.getElementById("count");
  var clear=document.getElementById("clearFilters");
  var empty=document.getElementById("emptyState");
  function digits(value){return (value||"").replace(/\\D/g,"");}
  function hasFilters(){return Boolean(state.city||state.country||state.spec||state.q);}
  function apply(){
    var n=0;
    cards.forEach(function(el){
      var ok=true;
      if(state.city && el.dataset.city.split("|").indexOf(state.city)<0) ok=false;
      if(state.country && el.dataset.country!==state.country) ok=false;
      if(state.spec && el.dataset.spec.split("|").indexOf(state.spec)<0) ok=false;
      if(state.q && el.dataset.text.indexOf(state.q)<0 && (!state.qDigits || el.dataset.text.indexOf(state.qDigits)<0)) ok=false;
      el.classList.toggle("hidden",!ok); if(ok) n++;
    });
    count.innerHTML="<b>"+n+"</b> clínica"+(n===1?"":"s")+(state.city?" en "+state.city:"")+(state.spec?" · "+state.spec:"");
    if(clear) clear.disabled=!hasFilters();
    if(empty) empty.classList.toggle("hidden",n!==0);
  }
  document.querySelectorAll(".chip").forEach(function(ch){
    ch.addEventListener("click",function(){
      var f=ch.dataset.f,v=ch.dataset.v;
      var on=state[f]===v; state[f]=on?null:v;
      document.querySelectorAll('.chip[data-f="'+f+'"]').forEach(function(o){o.classList.remove("on")});
      if(!on) ch.classList.add("on");
      apply();
    });
  });
  document.getElementById("q").addEventListener("input",function(e){state.q=e.target.value.toLowerCase().trim();state.qDigits=digits(state.q);apply();});
  if(clear) clear.addEventListener("click",function(){
    state={city:null,country:null,spec:null,q:"",qDigits:""};
    document.getElementById("q").value="";
    document.querySelectorAll(".chip").forEach(function(ch){ch.classList.remove("on")});
    apply();
  });
  function setupLogoCarousel(){
    document.querySelectorAll("[data-logo-carousel]").forEach(function(root){
      var track=root.querySelector(".logo-strip");
      var prev=root.querySelector('[data-logo-nav="prev"]');
      var next=root.querySelector('[data-logo-nav="next"]');
      var timer=null;
      var originals=[];
      if(!track) return;
      originals=[].slice.call(track.querySelectorAll(".mini-logo"));
      function ensureLoop(){
        if(track.querySelector(".logo-clone")||originals.length<2) return;
        originals.forEach(function(item){
          var clone=item.cloneNode(true);
          clone.classList.add("logo-clone");
          clone.setAttribute("aria-hidden","true");
          clone.setAttribute("tabindex","-1");
          track.appendChild(clone);
        });
      }
      function loopPoint(){
        var clone=track.querySelector(".logo-clone");
        return clone?clone.offsetLeft:0;
      }
      function maxScroll(){return Math.max(0,track.scrollWidth-track.clientWidth);}
      function step(){
        var item=track.querySelector(".mini-logo:not(.logo-failed)");
        return item?Math.max(120,item.getBoundingClientRect().width+12):160;
      }
      function normalize(){
        var point=loopPoint();
        if(point<=0) return;
        while(track.scrollLeft>=point) track.scrollLeft-=point;
        while(track.scrollLeft<0) track.scrollLeft+=point;
      }
      function update(){
        var max=maxScroll();
        if(prev) prev.disabled=max<=2;
        if(next) next.disabled=max<=2;
      }
      function move(dir){
        var max=maxScroll();
        var point=loopPoint();
        if(max<=2) return;
        if(point>0){
          if(dir<0&&track.scrollLeft<=2) track.scrollLeft=point+track.scrollLeft;
          track.scrollBy({left:step()*dir,behavior:"smooth"});
          window.setTimeout(function(){normalize();update();},360);
        }else if(dir>0&&track.scrollLeft>=max-2){
          track.scrollTo({left:0,behavior:"smooth"});
          window.setTimeout(update,260);
        }else if(dir<0&&track.scrollLeft<=2){
          track.scrollTo({left:max,behavior:"smooth"});
          window.setTimeout(update,260);
        }else{
          track.scrollBy({left:step()*dir,behavior:"smooth"});
          window.setTimeout(update,260);
        }
      }
      function pause(){
        if(timer){
          window.clearInterval(timer);
          timer=null;
        }
      }
      function play(){
        if(timer) return;
        if(window.matchMedia&&window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
        timer=window.setInterval(function(){move(1);},3200);
      }
      if(prev) prev.addEventListener("click",function(){pause();move(-1);});
      if(next) next.addEventListener("click",function(){pause();move(1);});
      track.addEventListener("scroll",function(){window.requestAnimationFrame(function(){normalize();update();});});
      root.addEventListener("pointerenter",pause);
      root.addEventListener("pointerleave",play);
      root.addEventListener("focusin",pause);
      root.addEventListener("focusout",play);
      window.addEventListener("resize",function(){normalize();update();});
      ensureLoop();
      update();
      play();
    });
  }
  function clean(value){return (value||"").trim();}
  function cleanUrl(value){
    var url=clean(value);
    if(url && !/^https?:\\/\\//i.test(url)) url="https://"+url;
    return url;
  }
  function setRecommendationStatus(message,tone){
    var node=document.getElementById("recommendStatus");
    if(!node) return;
    node.textContent=message||"";
    node.className="recommend-status"+(tone?" "+tone:"");
  }
  function setRecommendationBusy(form,busy){
    if(!form) return;
    [].slice.call(form.querySelectorAll("input,select,textarea,button")).forEach(function(node){
      if(node.id==="recommendTrap") return;
      node.disabled=busy;
    });
  }
  var recommendToggle=document.getElementById("recommendToggle");
  var recommendWrap=document.getElementById("recommendFormWrap");
  if(recommendToggle&&recommendWrap){
    recommendToggle.addEventListener("click",function(){
      var isHidden=recommendWrap.classList.toggle("hidden");
      recommendToggle.setAttribute("aria-expanded",isHidden?"false":"true");
      if(!isHidden){
        var first=document.getElementById("recommendClinicName");
        if(first) first.focus();
      }
    });
  }
  var recommendForm=document.getElementById("recommendClinicForm");
  if(recommendForm){
    recommendForm.addEventListener("submit",function(event){
      event.preventDefault();
      var config=window.VITALARGA_PUBLIC_CONFIG||{};
      var url=(config.supabaseUrl||"").replace(/\\/$/,"");
      var key=config.supabasePublishableKey||"";
      var name=clean(document.getElementById("recommendClinicName").value);
      var website=cleanUrl(document.getElementById("recommendClinicWebsite").value);
      var city=clean(document.getElementById("recommendClinicCity").value);
      var country=clean(document.getElementById("recommendClinicCountry").value)||"España";
      var requested=clean(document.getElementById("recommendClinicRequest").value)||"new_clinic";
      var note=clean(document.getElementById("recommendClinicNote").value);
      var trap=clean(document.getElementById("recommendTrap").value);
      if(!name){
        setRecommendationStatus("Indica el nombre de la clínica.", "error");
        return;
      }
      if(!website&&!city){
        setRecommendationStatus("Añade la web oficial o la ciudad para poder revisarla.", "error");
        return;
      }
      if(!url||!key){
        setRecommendationStatus("No se puede enviar ahora. Inténtalo más tarde.", "error");
        return;
      }
      setRecommendationBusy(recommendForm,true);
      setRecommendationStatus("Enviando recomendación...", "");
      fetch(url+"/rest/v1/rpc/public_recommend_clinic",{
        method:"POST",
        headers:{apikey:key,Authorization:"Bearer "+key,"Content-Type":"application/json"},
        body:JSON.stringify({
          p_clinic_name:name,
          p_website:website,
          p_city:city,
          p_country:country,
          p_requested_info:requested,
          p_note:note,
          p_honeypot:trap
        })
      }).then(function(response){
        if(!response.ok) throw new Error("No se pudo enviar");
        return response.json();
      }).then(function(result){
        if(result&&result.duplicate){
          setRecommendationStatus("Ya estaba en cola para revisión interna.", "ok");
          return;
        }
        recommendForm.reset();
        document.getElementById("recommendClinicCountry").value="España";
        setRecommendationStatus("Recibido. Queda como trabajo pendiente para revisión interna.", "ok");
      }).catch(function(){
        setRecommendationStatus("No se pudo enviar la recomendación. Prueba de nuevo más tarde.", "error");
      }).then(function(){
        setRecommendationBusy(recommendForm,false);
      });
    });
  }
  setupLogoCarousel();
  apply();
})();
</script>"""

INDEX_LD = '<script type="application/ld+json">' + json.dumps({
    "@context": "https://schema.org", "@type": "WebSite", "name": SITE,
    "url": BASE, "description": TAGLINE, "inLanguage": "es",
}, ensure_ascii=False) + "</script>"

RECOMMEND_SECTION = """
<section class="recommend" id="recomendar-clinica">
  <div class="recommend-inner">
    <div class="recommend-head">
      <div>
        <p class="kicker">Ayuda a completar la guía</p>
        <h2>Recomendar Clínica</h2>
        <p>Escribe una clínica, una pista o una fuente oficial. La revisaremos internamente antes de añadir o cambiar cualquier ficha.</p>
      </div>
      <button class="recommend-toggle" id="recommendToggle" type="button" aria-expanded="false" aria-controls="recommendFormWrap">Recomendar Clínica</button>
    </div>
    <div class="recommend-form-wrap hidden" id="recommendFormWrap">
      <form class="recommend-form" id="recommendClinicForm">
        <div>
          <label for="recommendClinicName">Clínica o pista</label>
          <input id="recommendClinicName" name="clinic_name" autocomplete="organization" required placeholder="Nombre, ciudad o pista útil">
        </div>
        <div>
          <label for="recommendClinicWebsite">Link oficial</label>
          <input id="recommendClinicWebsite" name="website" inputmode="url" placeholder="https://clinicaneleva.com/equipo/">
        </div>
        <div>
          <label for="recommendClinicCity">Ciudad</label>
          <input id="recommendClinicCity" name="city" autocomplete="address-level2" placeholder="Madrid, Barcelona, Marbella...">
        </div>
        <div>
          <label for="recommendClinicCountry">País</label>
          <input id="recommendClinicCountry" name="country" autocomplete="country-name" value="España">
        </div>
        <div class="recommend-wide">
          <label for="recommendClinicRequest">Qué revisar</label>
          <select id="recommendClinicRequest" name="requested_info">
            <option value="new_clinic">Añadir clínica nueva</option>
            <option value="specialists">Completar especialistas publicados</option>
            <option value="contact">Completar contacto público</option>
            <option value="locations">Completar sedes y acceso</option>
            <option value="services">Completar servicios</option>
            <option value="other">Otro dato claro</option>
          </select>
        </div>
        <div class="recommend-wide">
          <label for="recommendClinicNote">Nota breve</label>
          <textarea id="recommendClinicNote" name="note" maxlength="500" placeholder="Opcional: explica qué viste, qué falta o qué quieres que revisemos. No envíes datos médicos personales."></textarea>
        </div>
        <div class="recommend-trap" aria-hidden="true">
          <label for="recommendTrap">No rellenar</label>
          <input id="recommendTrap" name="company" tabindex="-1" autocomplete="off">
        </div>
        <div class="recommend-actions">
          <p class="recommend-status" id="recommendStatus">Nada se publica automáticamente.</p>
          <button class="recommend-submit" type="submit">Enviar recomendación</button>
        </div>
      </form>
    </div>
  </div>
</section>
"""

index = head(f"{SITE} — {TAGLINE}", "Todos queremos vivir más años con salud. Vitalarga te ayuda a encontrar clínica de medicina de longevidad por ciudad, país y especialidad.", "/", INDEX_LD) + f"""
<section class="hero">
<div class="hero-copy"><p class="kicker">La guía de las clínicas de longevidad</p>
<h1>Encuentra clínicas de longevidad con datos claros.</h1>
<p class="sub">Explora centros por ciudad, país y área médica con una guía independiente: sin rankings, sin publicidad y con revisión humana antes de publicar.</p></div>
<div class="finder" id="buscar">
<input id="q" type="search" placeholder="Busca por nombre, ciudad, especialidad o teléfono…" aria-label="Buscar clínica">
<div class="filter-grid">
<div class="fgroup"><span class="flabel">País</span><div class="chips">{country_chips}</div></div>
<div class="fgroup"><span class="flabel">Ciudad</span><div class="chips">{city_chips}</div></div>
<div class="fgroup"><span class="flabel">Especialidad</span><div class="chips">{spec_chips}</div></div>
</div>
</div>
</section>
<section class="logo-carousel" data-logo-carousel aria-label="Clínicas con logo en Vitalarga">
<button class="logo-nav" data-logo-nav="prev" type="button" aria-label="Logo anterior">&lsaquo;</button>
<div class="logo-viewport"><div class="logo-strip" tabindex="0" data-neutral-results="home-logos" aria-label="Logos de clínicas en la guía">{featured_logos}</div></div>
<button class="logo-nav" data-logo-nav="next" type="button" aria-label="Logo siguiente">&rsaquo;</button>
</section>
{RECOMMEND_SECTION}
<section class="results-section">
<div class="resbar"><p class="rescount" id="count"></p><button class="clear-btn" id="clearFilters" type="button">Limpiar filtros</button></div>
{ORDER_NOTE}
<div class="grid" data-neutral-results="home-clinics">{allcards}</div>
<p class="empty-state hidden" id="emptyState">No hay clínicas con esos filtros.</p>
<div class="note">¿Conoces una clínica de longevidad que no aparece aquí? Usa <a href="/#recomendar-clinica">Recomendar Clínica</a> y la evaluaremos según nuestros <a href="/sobre/">criterios de inclusión</a>. Aparecer en Vitalarga es gratuito — y no se puede pagar.</div>
</section>{NEUTRAL_ORDER_JS}{PUBLIC_SITE_CONFIG}{JS}""" + FOOTER

# --- fichas ---
def status_label(c):
    if c.get("status") == "preliminar":
        return "Ficha preliminar"
    if c.get("status") == "publicada":
        return "Ficha publicada"
    return str(c.get("status") or "").capitalize()

def section_heading(title, count=None):
    return f'<div class="profile-section-head"><h2>{h(title)}</h2></div>'

def facts_block(c):
    facts = []
    location = []
    seen = set()
    locations = clinic_locations(c)
    primary = primary_location(c)
    for value in (c.get("city"), c.get("region"), c.get("country")):
        value = str(value or "").strip()
        key = value.lower()
        if value and key not in seen:
            location.append(value)
            seen.add(key)
    if location:
        facts.append(("Ubicación", h(" · ".join(location))))
    if len(locations) > 1:
        facts.append(("Sedes", h(f"{len(locations)} sedes documentadas")))
    care_mode = care_mode_label(c.get("care_mode"))
    if care_mode and care_mode != "No consta":
        facts.append(("Modalidad", h(care_mode)))
    fallback_address = "" if explicit_clinic_locations(c) else c.get("address")
    address = first_text(location_address(primary), fallback_address)
    if address:
        maps_url = location_maps_url(primary, c)
        value = f'<a href="{h(maps_url)}" rel="nofollow noopener" target="_blank">{h(address)}</a>' if maps_url else h(address)
        facts.append(("Dirección principal", value))
    reviews_url = location_reviews_url(primary, c)
    if reviews_url:
        facts.append(("Valoraciones Google", f'<a href="{h(reviews_url)}" rel="nofollow noopener" target="_blank">Abrir valoraciones</a>'))
    if c.get("web") and external_url(c["web"]):
        url = external_url(c["web"])
        facts.append(("Web oficial", f'<a href="{h(url)}" rel="nofollow noopener" target="_blank">{h(display_url(url))}</a>'))
    if c.get("cities_extra"):
        facts.append(("También aparece en", h(" · ".join(c["cities_extra"]))))
    if c.get("status"):
        facts.append(("Estado en Vitalarga", h(status_label(c))))
    if not facts:
        return ""
    rows = "".join(f"<div><dt>{h(label)}</dt><dd>{value}</dd></div>" for label, value in facts)
    return f'<section class="profile-block" id="datos-clave">{section_heading("Datos clave")}<dl class="facts">{rows}</dl></section>'

def list_section(title, items, list_class="profile-list", section_id=""):
    items = visible_values(items)
    if not items:
        return ""
    id_attr = f' id="{h(section_id)}"' if section_id else ""
    return f'<section class="profile-block"{id_attr}>{section_heading(title, len(items))}<ul class="{h(list_class)}">' + "".join(f"<li>{h(item)}</li>" for item in items) + "</ul></section>"

def locations_block(c):
    locations = clinic_locations(c)
    if not locations:
        return ""
    rows = []
    multiple = len(locations) > 1
    for loc in locations:
        name = location_display_name(loc, c, multiple)
        address = location_address(loc)
        maps_url = location_maps_url(loc, c)
        reviews_url = location_reviews_url(loc, c)
        detail = location_detail(loc, c)
        actions = []
        if maps_url:
            actions.append(f'<a class="mini-action" href="{h(maps_url)}" rel="nofollow noopener" target="_blank">Google Maps</a>')
        if reviews_url:
            actions.append(f'<a class="mini-action" href="{h(reviews_url)}" rel="nofollow noopener" target="_blank">Valoraciones Google</a>')
        actions_html = f'<div class="location-actions">{"".join(actions)}</div>' if actions else ""
        rows.append(
            '<article class="location-item">'
            f'<h3>{h(name)}</h3>'
            f'<p>{h(detail or address or location_city(loc, c))}</p>'
            f'{actions_html}'
            '</article>'
        )
    block_class = "profile-block profile-location-block"
    if multiple:
        block_class += " profile-location-multiple"
    return f'<section class="{block_class}" id="sedes">' + section_heading("Sedes y acceso") + '<div class="location-list">' + "".join(rows) + "</div></section>"

def transparency_block(c):
    items = transparency_items(c)
    if not items:
        return ""
    rows = "".join(f"<div><dt>{h(label)}</dt><dd>{value}</dd></div>" for label, value in items)
    return f'<section class="profile-block" id="transparencia">{section_heading("Transparencia", len(items))}<dl class="transparency-grid">{rows}</dl></section>'

def tech_block(c):
    items = split_text_list(c.get("tech"))
    if not items:
        return ""
    if len(items) == 1:
        return f'<section class="profile-block" id="tecnologia">{section_heading("Tecnología destacada", len(items))}<p class="muted-copy">{h(items[0])}</p></section>'
    return list_section("Tecnología destacada", items, "pill-list", "tecnologia")

def contacto_block(c):
    """Bloque de contacto: solo campos verificados presentes en la ficha."""
    items = []
    if c.get("email"):
        email = str(c["email"]).strip()
        items.append(f'<li><b>Email:</b> <a href="mailto:{h(email)}">{h(email)}</a></li>')
    for label, tel, href in contact_phone_items(c):
        if href:
            items.append(f'<li><b>{h(label)}:</b> <a href="{h(href)}" rel="nofollow noopener" target="_blank">{h(tel)}</a></li>')
        else:
            items.append(f'<li><b>{h(label)}:</b> {h(tel)}</li>')
    if c.get("instagram"):
        handle, url = instagram_parts(c["instagram"])
        items.append(f'<li><b>Instagram:</b> <a href="{h(url)}" rel="nofollow noopener" target="_blank">{h(handle)}</a></li>')
    if not items:
        return ""
    return '<section class="profile-block" id="contacto">' + section_heading("Contacto publicado", len(items)) + '<ul class="contacto info-list">' + "".join(items) + "</ul></section>"

def profile_nav_item(label, target):
    return (
        f'<a href="{h(target)}" aria-label="{h(label)}">'
        f'<span class="profile-nav-label">{h(label)}</span></a>'
    )

def profile_nav(c, has_contact, has_tech, has_locations, has_transparency):
    items = []
    specs = visible_values(c.get("specialties"))
    services = visible_values(c.get("services"))
    units = visible_values(c.get("unidades"))
    professionals = visible_values(c.get("profesionales"))
    if specs:
        items.append(profile_nav_item("Especialidades", "#especialidades"))
    if services:
        items.append(profile_nav_item("Servicios", "#servicios"))
    if units:
        items.append(profile_nav_item("Unidades", "#unidades"))
    if has_tech:
        items.append(profile_nav_item("Tecnología", "#tecnologia"))
    if professionals:
        items.append(profile_nav_item("Especialistas", "#especialistas"))
    if has_locations:
        items.append(profile_nav_item("Sedes", "#sedes"))
    if has_transparency:
        items.append(profile_nav_item("Transparencia", "#transparencia"))
    if has_contact:
        items.append(profile_nav_item("Contacto", "#contacto"))
    if not items:
        return ""
    return '<div class="profile-jump"><span class="profile-jump-label">En esta ficha</span><nav class="profile-nav" aria-label="Contenido de la ficha">' + "".join(items) + "</nav></div>"

def ficha(c):
    tags = "".join(f'<span class="tag">{h(s)}</span>' for s in c["specialties"])
    locations = clinic_locations(c)
    datos = facts_block(c)
    contacto = contacto_block(c)
    areas = list_section("Áreas de especialidad", c["specialties"], section_id="especialidades")
    servicios = list_section("Servicios", c["services"], section_id="servicios")
    sedes = locations_block(c)
    unidades = list_section("Unidades y áreas clínicas", c.get("unidades"), section_id="unidades")
    tech = tech_block(c)
    equipo = list_section("Especialistas publicados por la clínica", c.get("profesionales"), section_id="especialistas")
    transparencia = transparency_block(c)
    nav = profile_nav(c, bool(contacto), bool(tech), bool(sedes), bool(transparencia))
    prelim = '<div class="note">Ficha preliminar: elaborada a partir de información pública básica, pendiente de ampliación y verificación detallada.</div>' if c["status"] == "preliminar" else ""
    extra = (" · " + " · ".join(c["cities_extra"])) if c.get("cities_extra") else ""
    city_label = c["city"] + extra
    hero_address = location_address(primary_location(c)) or (c.get("address") if not explicit_clinic_locations(c) and len(locations) <= 1 else "")
    loc = " · ".join(visible_values([city_label, c.get("country"), hero_address]))
    visit = ""
    if c.get("web") and external_url(c["web"]):
        visit_url = external_url(c["web"])
        visit = f'<a class="visit" href="{h(visit_url)}" rel="nofollow noopener" target="_blank">Visitar web oficial ↗</a>'
    sidebar = datos + contacto + visit
    sidebar_html = f'<aside class="clinic-side">{sidebar}</aside>' if sidebar else ""
    ld_obj = {
        "@context": "https://schema.org", "@type": "MedicalClinic",
        "name": c["name"], "url": c["web"], "address": c["address"],
        "medicalSpecialty": c["specialties"], "description": c["summary"],
    }
    _lf = logo_files.get(c["slug"]) or thumb_files.get(c["slug"])
    if _lf:
        _ls = "orig" if logo_files.get(c["slug"]) else "thumb"
        ld_obj["logo"] = f"{BASE}/assets/logos/{_ls}/{_lf}"
    if c.get("email"):
        ld_obj["email"] = c["email"]
    phone_values = [tel for _, tel, _ in contact_phone_items(c)]
    if phone_values:
        ld_obj["telephone"] = phone_values if len(phone_values) > 1 else phone_values[0]
    ld = '<script type="application/ld+json">' + json.dumps(ld_obj, ensure_ascii=False) + "</script>"
    return head(f'{c["name"]} — clínica de longevidad en {c["city"]} | {SITE}', c["summary"][:150], f'/clinica/{c["slug"]}/', ld) + f"""
<main class="ficha"><p class="crumbs"><a href="/">Vitalarga</a> → <a href="/ciudad/{slugify(c["city"])}/">{h(c["city"])}</a> → {h(c["name"])}</p>
<section class="clinic-intro"><div class="clinic-main">{logo_img(c, ficha=True)}<h1>{h(c["name"])}</h1><p class="loc">{h(loc)}</p>
<div class="tags">{tags}</div>
<p class="summary">{h(c["summary"])}</p>
{nav}
</div>{sidebar_html}</section>
<div class="profile-sections">
{areas}
{servicios}
{unidades}
{tech}
{equipo}
{sedes}
{transparencia}
</div>
{prelim}</main>""" + FOOTER

def ciudad_page(city):
    cs = cities[city]
    grid = "".join(card(c) for c in cs)
    return head(f"Clínicas de longevidad en {city} | {SITE}", f"Las {len(cs)} clínicas de medicina de longevidad documentadas en {city}.", f"/ciudad/{slugify(city)}/") + f"""
<div class="hero"><h1>Clínicas de longevidad en <em>{city}</em></h1><p class="sub">{len(cs)} clínica{"s" if len(cs)>1 else ""} documentada{"s" if len(cs)>1 else ""} en la guía.</p></div>
<div class="wrap">{ORDER_NOTE}<div class="grid" data-neutral-results="city:{h(city)}">{grid}</div></div>{NEUTRAL_ORDER_JS}""" + FOOTER

SOBRE = head(f"Sobre la guía | {SITE}", "Qué es Vitalarga y con qué criterios incluimos clínicas en la guía.", "/sobre/") + """
<div class="ficha"><h1>Sobre Vitalarga</h1>
<p class="summary">Vitalarga es una guía independiente de las clínicas de medicina de longevidad, escrita para quien quiere vivir más años con salud y no sabe por dónde empezar.</p>
<h2>Criterios de inclusión</h2>
<ul><li>Centro sanitario con actividad médica real (no solo estética o wellness).</li>
<li>Oferta específica de medicina de longevidad, preventiva o de precisión: biomarcadores, edad biológica, programas de seguimiento.</li>
<li>Equipo médico identificable y web con información verificable.</li></ul>
<h2>Lo que no hacemos</h2>
<ul><li>No emitimos recomendaciones médicas ni rankings de calidad asistencial.</li>
<li>Aparecer es gratuito y no se puede pagar: ninguna clínica influye en su ficha.</li>
<li>Las fichas se redactan a partir de información pública y se revisan manualmente antes de publicarse.</li></ul>
</div>""" + FOOTER

def legal_owner_block():
    rows = [
        ("Titular del sitio", h(LEGAL_OWNER["name"])),
        ("NIF", h(LEGAL_OWNER["tax_id"])),
        ("Domicilio", h(legal_owner_address())),
        (
            "Email administrativo",
            f'<a href="mailto:{h(LEGAL_OWNER["email"])}">{h(LEGAL_OWNER["email"])}</a>',
        ),
    ]
    return (
        '<section class="profile-block legal-owner" id="titular">'
        + section_heading("Datos del titular")
        + '<dl class="facts">'
        + "".join(f"<div><dt>{h(label)}</dt><dd>{value}</dd></div>" for label, value in rows)
        + "</dl></section>"
    )

def legal_page(slug, title, desc, intro, sections):
    body = "".join(
        f"<h2>{h(section_title)}</h2><p>{h(section_body)}</p>"
        for section_title, section_body in sections
    )
    return head(f"{title} | {SITE}", desc, f"/{slug}/") + f"""
<main class="ficha legal-page"><p class="crumbs"><a href="/">Vitalarga</a> → {h(title)}</p>
<h1>{h(title)}</h1>
<p class="summary">{h(intro)}</p>
{legal_owner_block()}
<div class="legal-copy">{body}</div>
</main>""" + FOOTER

LEGAL_PAGES = {
    "aviso-legal": legal_page(
        "aviso-legal",
        "Aviso legal",
        "Identificación del titular de Vitalarga y naturaleza informativa del sitio.",
        "Estos son los datos del titular legal de Vitalarga y el marco básico de uso del sitio.",
        [
            (
                "Naturaleza del sitio",
                "Vitalarga publica información editorial sobre clínicas de longevidad a partir de fuentes públicas y revisión manual. No presta servicios sanitarios, no diagnostica, no prescribe y no sustituye una consulta médica.",
            ),
            (
                "Relación con clínicas",
                "La aparición de una clínica en la guía no implica recomendación médica, ranking de calidad ni relación comercial con Vitalarga.",
            ),
            (
                "Contacto administrativo",
                "Para asuntos legales, administrativos o de corrección de información pública, utiliza el email administrativo indicado en esta página.",
            ),
        ],
    ),
    "privacidad": legal_page(
        "privacidad",
        "Política de privacidad",
        "Información básica sobre el responsable y el canal de contacto administrativo de Vitalarga.",
        "Esta página resume quién es el responsable del sitio y cómo contactar para asuntos de privacidad.",
        [
            (
                "Responsable",
                "El responsable del sitio Vitalarga es el titular legal indicado en esta página.",
            ),
            (
                "Contacto por email",
                "Si escribes al email administrativo, los datos incluidos en tu mensaje se usarán para atender y gestionar tu solicitud. Evita enviar datos de salud o documentación médica por este canal salvo que sea imprescindible.",
            ),
            (
                "Recomendar Clínica",
                "Si usas el formulario público para recomendar una clínica, guardaremos la información enviada como trabajo interno de revisión. No pedimos datos de salud ni publicamos automáticamente lo recibido.",
            ),
            (
                "Contenido público",
                "Las fichas de clínicas se elaboran con información pública y se revisan antes de publicarse. Las solicitudes de corrección pueden enviarse al email administrativo.",
            ),
        ],
    ),
    "cookies": legal_page(
        "cookies",
        "Política de cookies",
        "Información básica sobre medición técnica y estadística en Vitalarga.",
        "Esta página recoge la información básica sobre herramientas técnicas o estadísticas asociadas al sitio.",
        [
            (
                "Uso del sitio",
                "Vitalarga puede usar medición estadística del tráfico para entender el uso agregado de las páginas públicas y mejorar la guía.",
            ),
            (
                "Sin decisiones clínicas",
                "La medición de uso del sitio no se emplea para emitir recomendaciones médicas, valorar clínicas ni tomar decisiones sanitarias sobre usuarios.",
            ),
            (
                "Cambios futuros",
                "Si se incorporan formularios, cuentas de usuario, newsletter, publicidad u otras herramientas de terceros, esta política deberá revisarse antes de publicarse.",
            ),
        ],
    ),
}

# --- blog ---
posts = load_posts()

def blog_index():
    items = ""
    for p in posts:
        items += f'''<div class="card"><span class="loc">{p["date"]}</span>
<h3><a href="/blog/{p["slug"]}/">{p["title"]}</a></h3><p>{p["desc"]}</p></div>'''
    return head(f"Blog | {SITE}", "Guías y artículos sobre medicina de longevidad, escritos para pacientes: qué medir, qué preguntar, dónde acudir.", "/blog/") + f"""
<div class="hero"><h1>El blog de <em>Vitalarga</em></h1><p class="sub">Medicina de longevidad explicada para personas, no para médicos: qué medir, qué preguntar y dónde acudir.</p></div>
<div class="wrap"><div class="grid">{items}</div></div>""" + FOOTER

def blog_post(p):
    ld = '<script type="application/ld+json">' + json.dumps({
        "@context": "https://schema.org", "@type": "Article", "headline": p["title"],
        "datePublished": p["date"], "inLanguage": "es",
        "publisher": {"@type": "Organization", "name": SITE, "url": BASE},
    }, ensure_ascii=False) + "</script>"
    return head(f'{p["title"]} | {SITE}', p["desc"][:150], f'/blog/{p["slug"]}/', ld) + f"""
<div class="ficha"><p class="crumbs"><a href="/">Vitalarga</a> → <a href="/blog/">Blog</a></p>
<h1>{p["title"]}</h1><p class="loc">{p["date"]}</p>
{p["html"]}
<div class="note">Contenido divulgativo: no sustituye la valoración de un profesional sanitario. Vitalarga no emite recomendaciones médicas.</div>
</div>""" + FOOTER

def write_admin():
    src = os.path.join(ROOT, "admin")
    if not os.path.isdir(src):
        return
    dest = os.path.join(DIST, "admin")
    os.makedirs(dest, exist_ok=True)
    config = {
        "supabaseUrl": public_env("SUPABASE_URL"),
        "supabasePublishableKey": public_env("SUPABASE_PUBLISHABLE_KEY"),
    }
    config_json = json.dumps(config, ensure_ascii=False).replace("<", "\\u003c")
    html = open(os.path.join(src, "index.html"), encoding="utf-8").read()
    html = html.replace("__VITALARGA_ADMIN_CONFIG__", config_json)
    open(os.path.join(dest, "index.html"), "w", encoding="utf-8").write(html)
    shutil.copy(os.path.join(src, "admin.css"), os.path.join(dest, "admin.css"))

# --- write ---
if os.path.exists(DIST):
    shutil.rmtree(DIST)
os.makedirs(DIST)
open(os.path.join(DIST, "style.css"), "w", encoding="utf-8").write(CSS)
open(os.path.join(DIST, "favicon.svg"), "w", encoding="utf-8").write(FAVICON_SVG)
open(os.path.join(DIST, "index.html"), "w", encoding="utf-8").write(index)
os.makedirs(os.path.join(DIST, "sobre"))
open(os.path.join(DIST, "sobre", "index.html"), "w", encoding="utf-8").write(SOBRE)
for slug, html_doc in LEGAL_PAGES.items():
    d = os.path.join(DIST, slug)
    os.makedirs(d)
    open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(html_doc)
for c in clinics:
    d = os.path.join(DIST, "clinica", c["slug"])
    os.makedirs(d)
    open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(ficha(c))
for city in cities:
    d = os.path.join(DIST, "ciudad", slugify(city))
    os.makedirs(d)
    open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(ciudad_page(city))
for _sub, _files, _src in (("orig", logo_files, ORIG_DIR), ("thumb", thumb_files, THUMB_DIR)):
    if _files:
        _d = os.path.join(DIST, "assets", "logos", _sub)
        os.makedirs(_d, exist_ok=True)
        for _slug, _fn in _files.items():
            shutil.copy(os.path.join(_src, _fn), os.path.join(_d, _fn))
os.makedirs(os.path.join(DIST, "blog"))
open(os.path.join(DIST, "blog", "index.html"), "w", encoding="utf-8").write(blog_index())
for p in posts:
    d = os.path.join(DIST, "blog", p["slug"])
    os.makedirs(d)
    open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(blog_post(p))
write_admin()

# --- sitemap y robots ---
urls = ["/", "/sobre/", "/blog/"]
urls += [f"/{slug}/" for slug in LEGAL_PAGES]
urls += [f'/clinica/{c["slug"]}/' for c in clinics]
urls += [f"/ciudad/{slugify(ct)}/" for ct in cities]
urls += [f'/blog/{p["slug"]}/' for p in posts]
sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
sm += "".join(f"  <url><loc>{BASE}{u}</loc></url>\n" for u in urls)
sm += "</urlset>\n"
open(os.path.join(DIST, "sitemap.xml"), "w", encoding="utf-8").write(sm)
open(os.path.join(DIST, "robots.txt"), "w", encoding="utf-8").write(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
print(f"OK: {len(clinics)} clínicas, {len(cities)} ciudades, {len(specialties)} superespecialidades, {len(posts)} posts -> dist/")
