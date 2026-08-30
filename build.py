# -*- coding: utf-8 -*-
"""Generador estático de Diuvita — la guía de las clínicas de longevidad.
Uso: python3 build.py  ->  genera el sitio en dist/
Datos en data/clinics.json. Las fichas en pendientes/ NO se publican.
"""
import html, json, os, shutil, unicodedata, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
SITE = "Diuvita"
TAGLINE = "La guía de las clínicas de longevidad"
BASE = "https://www.diuvita.com"
PUBLIC_ENV_DEFAULTS = {
    "SUPABASE_URL": "https://twxhcmvzbpnrneywdece.supabase.co",
    "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_IHIMbYQacziyL1GcU6Mdtw_7AQdaCWg",
}

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
    source = env_value("DIUVITA_DATA_SOURCE", "json").strip().lower()
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
    for key in ("slug", "name", "city", "country", "address", "web", "summary", "status"):
        clinic[key] = clinic.get(key) or ""
    for key in ("tech", "email", "telefono", "instagram"):
        if key in clinic and clinic[key] is None:
            clinic[key] = ""
    for key in ("services", "specialties", "cities_extra", "profesionales", "unidades"):
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

clinics = [normalize_clinic(c) for c in load_clinics()]
clinics = [c for c in clinics if c.get("status") in ("publicada", "preliminar")]
clinics = sort_clinics(clinics)

# logos aprobados (descargados por GitHub Actions en assets/logos/)
# Homogeneidad: en tarjetas se usa la MINIATURA normalizada (thumb, <=260x64) dentro
# de una pastilla blanca de altura fija; en la ficha, el logo original.
LOGOS_FILE = os.path.join(ROOT, "data", "logos.json")
ORIG_DIR = os.path.join(ROOT, "assets", "logos", "orig")
THUMB_DIR = os.path.join(ROOT, "assets", "logos", "thumb")

def _find(dirpath, slug):
    if not os.path.isdir(dirpath):
        return None
    for fn in os.listdir(dirpath):
        if os.path.splitext(fn)[0] == slug:
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
:root{--bg:#f3f6f1;--surface:#fffdf8;--surface-strong:#fff;--ink:#17231f;--muted:#647168;--green:#1e7a5a;--green-deep:#123f32;--coral:#df6c4b;--line:#dfe6dc;--wash:#e9f2ec;--soft:#f8f4eb;--shadow:0 18px 44px rgba(23,35,31,.08)}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{font-family:'Source Sans 3',system-ui,sans-serif;background:var(--bg);color:var(--ink);line-height:1.58}
a{color:var(--green-deep);text-decoration:none}a:hover{text-decoration:underline;text-underline-offset:3px}
.site{position:sticky;top:0;z-index:10;padding:.95rem 5vw;display:flex;justify-content:space-between;align-items:center;gap:1rem;border-bottom:1px solid var(--line);background:rgba(255,253,248,.92);backdrop-filter:blur(14px)}
.site .logo{font-family:'Fraunces',Georgia,serif;font-size:1.55rem;font-weight:600;color:var(--ink)}
.site .logo em{color:var(--coral);font-style:normal}
.site nav{display:flex;align-items:center;gap:.35rem;flex-wrap:wrap;justify-content:flex-end}
.site nav a{padding:.42rem .7rem;border-radius:8px;color:var(--muted);font-weight:700;font-size:.95rem}
.site nav a:hover{background:var(--wash);color:var(--green-deep);text-decoration:none}
.hero{max-width:1180px;margin:0 auto;padding:2.35rem 5vw 1rem}
.hero-copy{max-width:860px}
.hero .kicker{color:var(--coral);font-size:.82rem;font-weight:800;text-transform:uppercase;letter-spacing:0}
.hero h1{max-width:24ch;margin:.55rem 0 0;font-family:'Fraunces',Georgia,serif;font-size:3.2rem;font-weight:500;line-height:1.05;text-wrap:balance}
.hero h1 em{color:var(--green);font-style:italic}
.hero p.sub{max-width:660px;margin:1rem 0 0;color:var(--muted);font-size:1.18rem}
.finder{margin-top:1.35rem;background:var(--surface-strong);border:1px solid var(--line);border-radius:8px;padding:.9rem;box-shadow:var(--shadow)}
.finder input{width:100%;min-height:3.35rem;font:inherit;font-size:1.04rem;padding:.75rem 1rem;border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--ink)}
.finder input:focus{outline:3px solid rgba(30,122,90,.2);border-color:var(--green)}
.filter-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.9rem;margin-top:.9rem}
.fgroup{min-width:0}
.fgroup .flabel{display:block;margin-bottom:.45rem;color:var(--muted);font-size:.74rem;font-weight:800;text-transform:uppercase;letter-spacing:0}
.chips{display:flex;flex-wrap:nowrap;gap:.38rem;overflow-x:auto;padding-bottom:.1rem;scrollbar-width:thin}
.chip{font:inherit;font-size:.86rem;line-height:1.2;padding:.38rem .65rem;border-radius:8px;border:1px solid var(--line);background:#fff;color:var(--ink);cursor:pointer}
.chip:hover{border-color:var(--green);color:var(--green-deep)}
.chip.on{background:var(--green);border-color:var(--green);color:#fff}
.hero-stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.7rem;margin-top:.85rem}
.hero-stats div{border-top:1px solid var(--line);padding-top:.7rem}
.hero-stats strong{display:block;font-size:1.55rem;line-height:1;color:var(--green-deep)}
.hero-stats span{display:block;margin-top:.2rem;color:var(--muted);font-size:.86rem}
.logo-strip{display:flex;gap:.65rem;overflow-x:auto;max-width:1180px;margin:.4rem auto 0;padding:.6rem 5vw 1.1rem;scrollbar-width:thin}
.mini-logo{flex:0 0 auto;height:42px;display:flex;align-items:center;padding:.35rem .7rem;border:1px solid var(--line);border-radius:8px;background:rgba(255,253,248,.82)}
.mini-logo img{max-width:126px;max-height:26px;object-fit:contain;display:block}
.results-section{max-width:1180px;margin:0 auto;padding:0 5vw 4rem}
.wrap{max-width:1180px;margin:0 auto;padding:0 5vw 4rem}
.resbar{position:sticky;top:66px;z-index:5;display:flex;align-items:center;justify-content:space-between;gap:.9rem;margin:.5rem 0 1rem;padding:.72rem .85rem;border:1px solid var(--line);border-radius:8px;background:rgba(255,253,248,.94);backdrop-filter:blur(12px)}
.rescount{color:var(--muted);font-size:.96rem}
.rescount b{color:var(--ink)}
.clear-btn{font:inherit;border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--green-deep);padding:.4rem .7rem;font-weight:800;cursor:pointer}
.clear-btn:disabled{cursor:not-allowed;opacity:.45}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(295px,1fr));gap:1rem}
.card{position:relative;display:flex;flex-direction:column;min-height:315px;padding:1rem;border:1px solid var(--line);border-radius:8px;background:var(--surface);box-shadow:0 1px 0 rgba(23,35,31,.03);transition:transform .15s ease,box-shadow .15s ease,border-color .15s ease}
.card:hover{transform:translateY(-2px);border-color:#cbd9ce;box-shadow:var(--shadow)}
.card-head{display:flex;align-items:flex-start;justify-content:space-between;gap:.7rem;min-height:48px}
.card .loc{display:block;margin-top:.35rem;color:var(--coral);font-size:.78rem;font-weight:800;text-transform:uppercase;letter-spacing:0}
.card h3{margin-top:.25rem;font-family:'Fraunces',Georgia,serif;font-size:1.28rem;font-weight:600;line-height:1.12}
.card h3 a{color:var(--ink)}
.card p{margin-top:.6rem;color:var(--muted);font-size:.96rem;flex:1}
.tags{display:flex;flex-wrap:wrap;gap:.35rem;margin-top:.8rem}
.tag{display:inline-flex;align-items:center;min-height:1.55rem;font-size:.78rem;padding:.18rem .55rem;border-radius:8px;background:var(--wash);color:var(--green-deep)}
.badge{display:inline-flex;align-items:center;min-height:1.45rem;font-size:.72rem;padding:.18rem .5rem;border-radius:8px;background:var(--soft);color:var(--muted);font-weight:800;white-space:nowrap}
.card-cta{align-self:flex-start;margin-top:1rem;padding:.48rem .75rem;border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--green-deep);font-weight:800}
.card-cta:hover{background:var(--wash);text-decoration:none}
.logobox{height:44px;width:fit-content;max-width:190px;display:flex;align-items:center;background:#fff;border:1px solid var(--line);border-radius:8px;padding:.35rem .65rem;align-self:flex-start}
.logobox img{max-height:29px;max-width:160px;object-fit:contain;display:block}
.flogo{height:62px;max-width:255px;margin-bottom:1rem}
.flogo img{max-height:43px;max-width:225px}
.hidden{display:none!important}
.empty-state{padding:2rem;border:1px dashed #cbd9ce;border-radius:8px;background:rgba(255,253,248,.72);color:var(--muted);text-align:center}
.ficha{max-width:1120px;margin:0 auto;padding:2.1rem 5vw 4rem}
.crumbs{font-size:.9rem;color:var(--muted);margin-bottom:1.25rem}
.clinic-intro{display:grid;grid-template-columns:minmax(0,1fr) 330px;gap:2rem;align-items:start}
.clinic-main h1,.ficha>h1{font-family:'Fraunces',Georgia,serif;font-size:3.05rem;font-weight:500;line-height:1.04;text-wrap:balance}
.ficha .loc{color:var(--coral);text-transform:uppercase;font-size:.86rem;font-weight:800;margin:.6rem 0 1rem;letter-spacing:0}
.ficha .summary{max-width:720px;margin-top:1rem;font-size:1.18rem;color:var(--ink)}
.profile-nav{display:flex;flex-wrap:wrap;gap:.45rem;margin-top:1rem}
.profile-nav a{display:inline-flex;align-items:center;gap:.35rem;min-height:1.85rem;padding:.26rem .42rem .26rem .62rem;border:1px solid var(--line);border-radius:8px;background:var(--surface);color:var(--green-deep);font-size:.84rem;font-weight:800}
.profile-nav a:hover{background:var(--wash);text-decoration:none}
.profile-nav span{display:inline-flex;align-items:center;justify-content:center;min-width:1.35rem;min-height:1.35rem;border-radius:8px;background:var(--wash);font-size:.75rem;color:var(--green-deep)}
.clinic-side{display:grid;gap:1rem;padding:1rem;border:1px solid var(--line);border-radius:8px;background:var(--surface);box-shadow:0 1px 0 rgba(23,35,31,.03)}
.clinic-side .profile-block{margin-top:0;padding:0;border-top:0;background:transparent}
.clinic-side h2{margin-top:0}
.profile-sections{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem;margin-top:1.5rem}
.profile-block{padding:1rem;border-top:1px solid var(--line);background:rgba(255,253,248,.46)}
.ficha h2{font-family:'Fraunces',Georgia,serif;font-weight:600;font-size:1.22rem;margin:0 0 .55rem}
.ficha ul{padding-left:1.1rem;color:var(--muted)}
.facts{display:grid;grid-template-columns:1fr;gap:.75rem;margin:.75rem 0 0}
.facts div{border-top:1px solid var(--line);padding-top:.55rem}
.facts dt{font-size:.74rem;text-transform:uppercase;color:var(--coral);font-weight:800;letter-spacing:0}
.facts dd{margin:0;color:var(--ink);overflow-wrap:anywhere}
.info-list{display:grid;gap:.38rem}
.pill-list{display:flex;flex-wrap:wrap;gap:.45rem;list-style:none;padding-left:0!important}
.pill-list li{font-size:.86rem;padding:.3rem .62rem;border-radius:8px;background:var(--wash);color:var(--green-deep)}
.contacto{list-style:none;padding-left:0!important}
.contacto li{margin:.25rem 0;overflow-wrap:anywhere}
.contacto b{color:var(--ink);font-weight:700}
.muted-copy{color:var(--muted)}
.visit{display:inline-flex;justify-content:center;align-items:center;margin-top:.25rem;background:var(--green);color:#fff;padding:.68rem 1rem;border-radius:8px;font-weight:800;text-align:center}
.visit:hover{text-decoration:none;background:var(--green-deep)}
.note{background:var(--soft);border:1px solid var(--line);border-radius:8px;padding:1rem 1.1rem;font-size:.93rem;color:var(--muted);margin-top:1.4rem}
footer{border-top:1px solid var(--line);padding:2rem 5vw;color:var(--muted);font-size:.9rem;background:rgba(255,253,248,.56)}
footer p{max-width:1120px;margin:0 auto}
@media(prefers-reduced-motion:reduce){.card{transition:none}.card:hover{transform:none}}
@media(max-width:860px){.hero{padding-top:2rem}.hero h1{font-size:2.65rem}.filter-grid,.hero-stats,.profile-sections,.clinic-intro{grid-template-columns:1fr}.clinic-side{order:2}.resbar{position:static;align-items:flex-start;flex-direction:column}.clear-btn{width:100%}}
@media(max-width:640px){.site{position:static;align-items:flex-start;flex-direction:column}.site nav{justify-content:flex-start}.hero h1{font-size:2.25rem}.hero p.sub,.ficha .summary{font-size:1.05rem}.grid{grid-template-columns:1fr}.card{min-height:auto}.clinic-main h1,.ficha>h1{font-size:2.2rem}.logo-strip{padding-left:5vw}.facts{grid-template-columns:1fr}}
"""

HEAD = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website"><meta property="og:site_name" content="Diuvita">
<meta property="og:title" content="{title}"><meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}"><meta property="og:locale" content="es_ES">
<meta name="twitter:card" content="summary">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;0,9..144,600;1,9..144,500&family=Source+Sans+3:wght@400;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/style.css">
<script data-goatcounter="https://diuvita.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
{jsonld}</head><body>
<header class="site"><a class="logo" href="/">Diuvita<em>.</em></a>
<nav><a href="/#buscar">Buscar clínica</a><a href="/blog/">Blog</a><a href="/sobre/">Sobre la guía</a></nav></header>
"""

def head(title, desc, path, jsonld=""):
    return HEAD.format(title=title, desc=desc, url=BASE + path, jsonld=jsonld)

FOOTER = """<footer><p><strong>Diuvita</strong> — {tag}. Guía informativa e independiente: no emitimos recomendaciones médicas, no hacemos rankings y ninguna clínica paga por aparecer. Cada ficha se elabora a partir de información pública y se revisa manualmente.</p></footer></body></html>""".format(tag=TAGLINE)

def attrs(c):
    extra = c.get("cities_extra", [])
    all_cities = "|".join([c["city"]] + extra)
    search_parts = [
        c["name"],
        c["city"],
        c["country"],
        c.get("region", ""),
        c.get("address", ""),
        c.get("summary", ""),
        c.get("tech", ""),
        " ".join(c["specialties"]),
        " ".join(c["services"]),
        " ".join(c.get("unidades", [])),
        " ".join(c.get("profesionales", [])),
    ]
    search_text = " ".join(str(part).lower() for part in search_parts if part)
    return f'data-city="{h(all_cities)}" data-country="{h(c["country"])}" data-spec="{h("|".join(c["specialties"]))}" data-text="{h(search_text)}"'

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
    return f'<span class="{cls}"><img src="/assets/logos/{sub}/{h(fn)}" alt="Logo de {h(c["name"])}" loading="lazy"></span>'

def card(c):
    badge = '<span class="badge">Preliminar</span>' if c["status"] == "preliminar" else ""
    extra = (" · " + " · ".join(c["cities_extra"])) if c.get("cities_extra") else ""
    tags = "".join(f'<span class="tag">{h(s)}</span>' for s in c["specialties"])
    summary = h(c["summary"][:150]) + ("…" if len(c["summary"]) > 150 else "")
    return f'''<article class="card" {attrs(c)}><div class="card-head">{logo_img(c)}{badge}</div>
<span class="loc">{h(c["city"])}{h(extra)} · {h(c["country"])}</span>
<h3><a href="/clinica/{h(c["slug"])}/">{h(c["name"])}</a></h3>
<p>{summary}</p>
<div class="tags">{tags}</div><a class="card-cta" href="/clinica/{h(c["slug"])}/">Ver ficha</a></article>'''

# --- index ---
city_chips = "".join(f'<button class="chip" data-f="city" data-v="{h(ct)}">{h(ct)}</button>' for ct in city_order)
country_chips = "".join(f'<button class="chip" data-f="country" data-v="{h(co)}">{h(co)}</button>' for co in countries)
spec_chips = "".join(f'<button class="chip" data-f="spec" data-v="{h(s)}">{h(s)}</button>' for s in specialties)
allcards = "".join(card(c) for c in clinics)
featured_logo_clinics = [c for c in clinics if c.get("slug") in thumb_files][:12]
featured_logos = "".join(
    f'<span class="mini-logo"><img src="/assets/logos/thumb/{h(thumb_files[c["slug"]])}" alt="{h(c["name"])}" loading="lazy"></span>'
    for c in featured_logo_clinics
)
hero_stats = f"""
<div class="hero-stats" aria-label="Resumen de la guía">
  <div><strong>{len(clinics)}</strong><span>clínicas visibles</span></div>
  <div><strong>{len(cities)}</strong><span>ciudades</span></div>
  <div><strong>{len(countries)}</strong><span>países</span></div>
  <div><strong>{len(specialties)}</strong><span>especialidades</span></div>
</div>"""

JS = """<script>
(function(){
  var state={city:null,country:null,spec:null,q:""};
  var cards=[].slice.call(document.querySelectorAll(".grid .card"));
  var count=document.getElementById("count");
  var clear=document.getElementById("clearFilters");
  var empty=document.getElementById("emptyState");
  function hasFilters(){return Boolean(state.city||state.country||state.spec||state.q);}
  function apply(){
    var n=0;
    cards.forEach(function(el){
      var ok=true;
      if(state.city && el.dataset.city.split("|").indexOf(state.city)<0) ok=false;
      if(state.country && el.dataset.country!==state.country) ok=false;
      if(state.spec && el.dataset.spec.split("|").indexOf(state.spec)<0) ok=false;
      if(state.q && el.dataset.text.indexOf(state.q)<0) ok=false;
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
  document.getElementById("q").addEventListener("input",function(e){state.q=e.target.value.toLowerCase().trim();apply();});
  if(clear) clear.addEventListener("click",function(){
    state={city:null,country:null,spec:null,q:""};
    document.getElementById("q").value="";
    document.querySelectorAll(".chip").forEach(function(ch){ch.classList.remove("on")});
    apply();
  });
  apply();
})();
</script>"""

INDEX_LD = '<script type="application/ld+json">' + json.dumps({
    "@context": "https://schema.org", "@type": "WebSite", "name": SITE,
    "url": BASE, "description": TAGLINE, "inLanguage": "es",
}, ensure_ascii=False) + "</script>"

index = head(f"{SITE} — {TAGLINE}", "Todos queremos vivir más años con salud. Diuvita te ayuda a encontrar clínica de medicina de longevidad por ciudad, país y especialidad.", "/", INDEX_LD) + f"""
<section class="hero">
<div class="hero-copy"><p class="kicker">La guía de las clínicas de longevidad</p>
<h1>Encuentra clínicas de longevidad con datos claros.</h1>
<p class="sub">Compara centros por ciudad, país y área médica con una guía independiente: sin rankings, sin publicidad y con revisión humana antes de publicar.</p></div>
<div class="finder" id="buscar">
<input id="q" type="search" placeholder="Busca por nombre, ciudad o especialidad…" aria-label="Buscar clínica">
<div class="filter-grid">
<div class="fgroup"><span class="flabel">País</span><div class="chips">{country_chips}</div></div>
<div class="fgroup"><span class="flabel">Ciudad</span><div class="chips">{city_chips}</div></div>
<div class="fgroup"><span class="flabel">Superespecialidad</span><div class="chips">{spec_chips}</div></div>
</div>
</div>
{hero_stats}
</section>
<section class="logo-strip">{featured_logos}</section>
<section class="results-section">
<div class="resbar"><p class="rescount" id="count"></p><button class="clear-btn" id="clearFilters" type="button">Limpiar filtros</button></div>
<div class="grid">{allcards}</div>
<p class="empty-state hidden" id="emptyState">No hay clínicas con esos filtros.</p>
<div class="note">¿Diriges una clínica de longevidad que no aparece aquí? Escríbenos y la evaluaremos según nuestros <a href="/sobre/">criterios de inclusión</a>. Aparecer en Diuvita es gratuito — y no se puede pagar.</div>
</section>{JS}""" + FOOTER

# --- fichas ---
def status_label(c):
    if c.get("status") == "preliminar":
        return "Ficha preliminar"
    if c.get("status") == "publicada":
        return "Ficha publicada"
    return str(c.get("status") or "").capitalize()

def facts_block(c):
    facts = []
    location = []
    seen = set()
    for value in (c.get("city"), c.get("region"), c.get("country")):
        value = str(value or "").strip()
        key = value.lower()
        if value and key not in seen:
            location.append(value)
            seen.add(key)
    if location:
        facts.append(("Ubicación", h(" · ".join(location))))
    if c.get("address"):
        facts.append(("Dirección", h(c["address"])))
    if c.get("web") and external_url(c["web"]):
        url = external_url(c["web"])
        facts.append(("Web oficial", f'<a href="{h(url)}" rel="nofollow noopener" target="_blank">{h(display_url(url))}</a>'))
    if c.get("cities_extra"):
        facts.append(("También aparece en", h(" · ".join(c["cities_extra"]))))
    if c.get("status"):
        facts.append(("Estado en Diuvita", h(status_label(c))))
    if not facts:
        return ""
    rows = "".join(f"<div><dt>{h(label)}</dt><dd>{value}</dd></div>" for label, value in facts)
    return f'<section class="profile-block" id="datos-clave"><h2>Datos clave</h2><dl class="facts">{rows}</dl></section>'

def list_section(title, items, list_class="info-list", section_id=""):
    items = visible_values(items)
    if not items:
        return ""
    id_attr = f' id="{h(section_id)}"' if section_id else ""
    return f'<section class="profile-block"{id_attr}><h2>{h(title)}</h2><ul class="{h(list_class)}">' + "".join(f"<li>{h(item)}</li>" for item in items) + "</ul></section>"

def tech_block(c):
    items = split_text_list(c.get("tech"))
    if not items:
        return ""
    if len(items) == 1:
        return f'<section class="profile-block" id="tecnologia"><h2>Tecnología destacada</h2><p class="muted-copy">{h(items[0])}</p></section>'
    return list_section("Tecnología destacada", items, "pill-list", "tecnologia")

def contacto_block(c):
    """Bloque de contacto: solo campos verificados presentes en la ficha."""
    items = []
    if c.get("email"):
        email = str(c["email"]).strip()
        items.append(f'<li><b>Email:</b> <a href="mailto:{h(email)}">{h(email)}</a></li>')
    if c.get("telefono"):
        tel = str(c["telefono"]).strip()
        tel_href = re.sub(r"[^0-9+]", "", tel)
        items.append(f'<li><b>Tel\u00e9fono:</b> <a href="tel:{h(tel_href)}">{h(tel)}</a></li>')
    if c.get("instagram"):
        handle, url = instagram_parts(c["instagram"])
        items.append(f'<li><b>Instagram:</b> <a href="{h(url)}" rel="nofollow noopener" target="_blank">{h(handle)}</a></li>')
    if not items:
        return ""
    return '<section class="profile-block" id="contacto"><h2>Contacto publicado</h2><ul class="contacto info-list">' + "".join(items) + "</ul></section>"

def profile_nav_item(label, count, target):
    return f'<a href="{h(target)}">{h(label)}<span>{h(count)}</span></a>'

def profile_nav(c, has_contact, has_tech):
    items = []
    specs = visible_values(c.get("specialties"))
    services = visible_values(c.get("services"))
    units = visible_values(c.get("unidades"))
    professionals = visible_values(c.get("profesionales"))
    if specs:
        items.append(profile_nav_item("Especialidades", len(specs), "#especialidades"))
    if services:
        items.append(profile_nav_item("Servicios", len(services), "#servicios"))
    if units:
        items.append(profile_nav_item("Unidades", len(units), "#unidades"))
    if has_tech:
        items.append(profile_nav_item("Tecnología", len(split_text_list(c.get("tech"))), "#tecnologia"))
    if professionals:
        items.append(profile_nav_item("Especialistas", len(professionals), "#especialistas"))
    if has_contact:
        contact_count = sum(1 for key in ("email", "telefono", "instagram") if c.get(key))
        items.append(profile_nav_item("Contacto", contact_count, "#contacto"))
    if not items:
        return ""
    return '<nav class="profile-nav" aria-label="Contenido de la ficha">' + "".join(items) + "</nav>"

def ficha(c):
    tags = "".join(f'<span class="tag">{h(s)}</span>' for s in c["specialties"])
    datos = facts_block(c)
    contacto = contacto_block(c)
    areas = list_section("Áreas de especialidad", c["specialties"], section_id="especialidades")
    servicios = list_section("Servicios", c["services"], section_id="servicios")
    unidades = list_section("Unidades y áreas clínicas", c.get("unidades"), section_id="unidades")
    tech = tech_block(c)
    equipo = list_section("Especialistas publicados por la clínica", c.get("profesionales"), section_id="especialistas")
    nav = profile_nav(c, bool(contacto), bool(tech))
    prelim = '<div class="note">Ficha preliminar: elaborada a partir de información pública básica, pendiente de ampliación y verificación detallada.</div>' if c["status"] == "preliminar" else ""
    extra = (" · " + " · ".join(c["cities_extra"])) if c.get("cities_extra") else ""
    city_label = c["city"] + extra
    loc = " · ".join(visible_values([city_label, c.get("country"), c.get("address")]))
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
    if c.get("telefono"):
        ld_obj["telephone"] = c["telefono"]
    ld = '<script type="application/ld+json">' + json.dumps(ld_obj, ensure_ascii=False) + "</script>"
    return head(f'{c["name"]} — clínica de longevidad en {c["city"]} | {SITE}', c["summary"][:150], f'/clinica/{c["slug"]}/', ld) + f"""
<main class="ficha"><p class="crumbs"><a href="/">Diuvita</a> → <a href="/ciudad/{slugify(c["city"])}/">{h(c["city"])}</a> → {h(c["name"])}</p>
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
</div>
{prelim}</main>""" + FOOTER

def ciudad_page(city):
    cs = cities[city]
    grid = "".join(card(c) for c in cs)
    return head(f"Clínicas de longevidad en {city} | {SITE}", f"Las {len(cs)} clínicas de medicina de longevidad documentadas en {city}.", f"/ciudad/{slugify(city)}/") + f"""
<div class="hero"><h1>Clínicas de longevidad en <em>{city}</em></h1><p class="sub">{len(cs)} clínica{"s" if len(cs)>1 else ""} documentada{"s" if len(cs)>1 else ""} en la guía.</p></div>
<div class="wrap"><div class="grid">{grid}</div></div>""" + FOOTER

SOBRE = head(f"Sobre la guía | {SITE}", "Qué es Diuvita y con qué criterios incluimos clínicas en la guía.", "/sobre/") + """
<div class="ficha"><h1>Sobre Diuvita</h1>
<p class="summary">Diuvita (del latín <em>diu</em>, «por largo tiempo», y <em>vita</em>, «vida») es una guía independiente de las clínicas de medicina de longevidad, escrita para quien quiere vivir más años con salud y no sabe por dónde empezar.</p>
<h2>Criterios de inclusión</h2>
<ul><li>Centro sanitario con actividad médica real (no solo estética o wellness).</li>
<li>Oferta específica de medicina de longevidad, preventiva o de precisión: biomarcadores, edad biológica, programas de seguimiento.</li>
<li>Equipo médico identificable y web con información verificable.</li></ul>
<h2>Lo que no hacemos</h2>
<ul><li>No emitimos recomendaciones médicas ni rankings de calidad asistencial.</li>
<li>Aparecer es gratuito y no se puede pagar: ninguna clínica influye en su ficha.</li>
<li>Las fichas se redactan a partir de información pública y se revisan manualmente antes de publicarse.</li></ul>
</div>""" + FOOTER

# --- blog ---
posts = load_posts()

def blog_index():
    items = ""
    for p in posts:
        items += f'''<div class="card"><span class="loc">{p["date"]}</span>
<h3><a href="/blog/{p["slug"]}/">{p["title"]}</a></h3><p>{p["desc"]}</p></div>'''
    return head(f"Blog | {SITE}", "Guías y artículos sobre medicina de longevidad, escritos para pacientes: qué medir, qué preguntar, dónde acudir.", "/blog/") + f"""
<div class="hero"><h1>El blog de <em>Diuvita</em></h1><p class="sub">Medicina de longevidad explicada para personas, no para médicos: qué medir, qué preguntar y dónde acudir.</p></div>
<div class="wrap"><div class="grid">{items}</div></div>""" + FOOTER

def blog_post(p):
    ld = '<script type="application/ld+json">' + json.dumps({
        "@context": "https://schema.org", "@type": "Article", "headline": p["title"],
        "datePublished": p["date"], "inLanguage": "es",
        "publisher": {"@type": "Organization", "name": SITE, "url": BASE},
    }, ensure_ascii=False) + "</script>"
    return head(f'{p["title"]} | {SITE}', p["desc"][:150], f'/blog/{p["slug"]}/', ld) + f"""
<div class="ficha"><p class="crumbs"><a href="/">Diuvita</a> → <a href="/blog/">Blog</a></p>
<h1>{p["title"]}</h1><p class="loc">{p["date"]}</p>
{p["html"]}
<div class="note">Contenido divulgativo: no sustituye la valoración de un profesional sanitario. Diuvita no emite recomendaciones médicas.</div>
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
    html = html.replace("__DIUVITA_ADMIN_CONFIG__", config_json)
    open(os.path.join(dest, "index.html"), "w", encoding="utf-8").write(html)
    shutil.copy(os.path.join(src, "admin.css"), os.path.join(dest, "admin.css"))

# --- write ---
if os.path.exists(DIST):
    shutil.rmtree(DIST)
os.makedirs(DIST)
open(os.path.join(DIST, "style.css"), "w", encoding="utf-8").write(CSS)
open(os.path.join(DIST, "index.html"), "w", encoding="utf-8").write(index)
os.makedirs(os.path.join(DIST, "sobre"))
open(os.path.join(DIST, "sobre", "index.html"), "w", encoding="utf-8").write(SOBRE)
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
urls += [f'/clinica/{c["slug"]}/' for c in clinics]
urls += [f"/ciudad/{slugify(ct)}/" for ct in cities]
urls += [f'/blog/{p["slug"]}/' for p in posts]
sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
sm += "".join(f"  <url><loc>{BASE}{u}</loc></url>\n" for u in urls)
sm += "</urlset>\n"
open(os.path.join(DIST, "sitemap.xml"), "w", encoding="utf-8").write(sm)
open(os.path.join(DIST, "robots.txt"), "w", encoding="utf-8").write(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
print(f"OK: {len(clinics)} clínicas, {len(cities)} ciudades, {len(specialties)} superespecialidades, {len(posts)} posts -> dist/")
