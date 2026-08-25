# -*- coding: utf-8 -*-
"""Generador estático de Diuvita — la guía de las clínicas de longevidad.
Uso: python3 build.py  ->  genera el sitio en dist/
Datos en data/clinics.json. Las fichas en pendientes/ NO se publican.
"""
import json, os, shutil, unicodedata

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
SITE = "Diuvita"
TAGLINE = "La guía de las clínicas de longevidad"
BASE = "https://diuvita.com"

import re
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

with open(os.path.join(ROOT, "data", "clinics.json"), encoding="utf-8") as f:
    clinics = json.load(f)
clinics = [c for c in clinics if c.get("status") in ("publicada", "preliminar")]

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
:root{--bg:#f7f3ea;--ink:#182420;--muted:#5f6b63;--green:#1e7a5a;--green-deep:#134737;--coral:#e0704a;--card:#fffdf8;--line:#e6dfd0;--wash:#ecf3ee}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{font-family:'Source Sans 3',system-ui,sans-serif;background:var(--bg);color:var(--ink);line-height:1.6}
a{color:var(--green);text-decoration:none}a:hover{text-decoration:underline}
header.site{padding:1.1rem 5vw;display:flex;justify-content:space-between;align-items:baseline}
header.site .logo{font-family:'Fraunces',Georgia,serif;font-size:1.6rem;font-weight:600;color:var(--ink)}
header.site .logo em{color:var(--coral);font-style:normal}
header.site nav a{margin-left:1.2rem;color:var(--muted);font-size:.95rem}
/* HERO */
.hero{padding:3.5rem 5vw 2.5rem;max-width:1050px;margin:0 auto;text-align:center}
.hero .kicker{text-transform:uppercase;letter-spacing:.14em;font-size:.8rem;color:var(--coral);font-weight:600}
.hero h1{font-family:'Fraunces',Georgia,serif;font-size:clamp(2.1rem,5.5vw,3.6rem);font-weight:500;line-height:1.12;margin:.7rem auto 0;max-width:17ch;text-wrap:balance}
.hero h1 em{font-style:italic;color:var(--green)}
.hero p.sub{margin:1.1rem auto 0;font-size:1.15rem;color:var(--muted);max-width:44ch}
/* SEARCH */
.finder{max-width:860px;margin:2.2rem auto 0;background:var(--card);border:1px solid var(--line);border-radius:18px;padding:1.3rem 1.4rem;box-shadow:0 10px 30px rgba(24,36,32,.06);text-align:left}
.finder input{width:100%;font:inherit;font-size:1.05rem;padding:.75rem 1rem;border:1.5px solid var(--line);border-radius:12px;background:#fff;color:var(--ink)}
.finder input:focus{outline:2px solid var(--green);border-color:var(--green)}
.fgroup{margin-top:1rem}
.fgroup .flabel{font-size:.72rem;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);font-weight:600}
.chips{display:flex;flex-wrap:wrap;gap:.45rem;margin-top:.45rem}
.chip{font:inherit;font-size:.86rem;padding:.32rem .85rem;border-radius:99px;border:1.5px solid var(--line);background:#fff;color:var(--ink);cursor:pointer}
.chip:hover{border-color:var(--green)}
.chip.on{background:var(--green);border-color:var(--green);color:#fff}
.rescount{margin:1.6rem auto .4rem;max-width:1050px;padding:0 5vw;color:var(--muted);font-size:.95rem}
.rescount b{color:var(--ink)}
/* GRID */
.wrap{padding:0 5vw 4rem;max-width:1050px;margin:0 auto}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:1.1rem}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:1.3rem;display:flex;flex-direction:column;gap:.55rem;transition:transform .15s,box-shadow .15s}
.card:hover{transform:translateY(-3px);box-shadow:0 12px 28px rgba(24,36,32,.09)}
.card .loc{font-size:.8rem;color:var(--coral);letter-spacing:.06em;text-transform:uppercase;font-weight:600}
.card h3{font-family:'Fraunces',Georgia,serif;font-weight:600;font-size:1.2rem}
.card h3 a{color:var(--ink)}
.card p{font-size:.94rem;color:var(--muted);flex:1}
.tags{display:flex;flex-wrap:wrap;gap:.35rem}
.tag{font-size:.74rem;padding:.16rem .6rem;border-radius:99px;background:var(--wash);color:var(--green-deep)}
.badge{display:inline-block;font-size:.7rem;padding:.14rem .5rem;border-radius:99px;background:#f0e9da;color:var(--muted);margin-left:.4rem;vertical-align:middle}
.logobox{height:46px;width:fit-content;max-width:200px;display:flex;align-items:center;background:#fff;border:1px solid var(--line);border-radius:9px;padding:.35rem .7rem;margin-bottom:.35rem;align-self:flex-start}
.logobox img{max-height:30px;max-width:170px;object-fit:contain;display:block}
.flogo{height:60px;max-width:250px;margin-bottom:1rem}
.flogo img{max-height:42px;max-width:220px}
.hidden{display:none}
/* FICHA */
.ficha{max-width:760px;margin:0 auto;padding:2.5rem 5vw 4rem}
.ficha h1{font-family:'Fraunces',Georgia,serif;font-size:2.3rem;font-weight:500}
.ficha .loc{color:var(--coral);text-transform:uppercase;letter-spacing:.06em;font-size:.85rem;font-weight:600;margin:.3rem 0 1rem}
.ficha .tags{margin-bottom:1.4rem}
.ficha .summary{font-size:1.13rem;margin-bottom:1.5rem}
.ficha h2{font-family:'Fraunces',Georgia,serif;font-weight:600;font-size:1.2rem;margin:1.5rem 0 .5rem}
.ficha ul{padding-left:1.2rem;color:var(--muted)}
.ficha .visit{display:inline-block;margin-top:2rem;background:var(--green);color:#fff;padding:.65rem 1.4rem;border-radius:10px;font-weight:600}
.ficha .visit:hover{text-decoration:none;background:var(--green-deep)}
.note{background:#f2ecdf;border:1px solid var(--line);border-radius:12px;padding:1rem 1.2rem;font-size:.9rem;color:var(--muted);margin-top:2.2rem}
footer{border-top:1px solid var(--line);padding:2rem 5vw;color:var(--muted);font-size:.88rem}
.crumbs{font-size:.85rem;color:var(--muted);margin-bottom:1.5rem}
@media(prefers-reduced-motion:reduce){.card{transition:none}}
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
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;0,9..144,600;1,9..144,500&family=Source+Sans+3:wght@400;600&display=swap" rel="stylesheet">
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
    return f'data-city="{all_cities}" data-country="{c["country"]}" data-spec="{"|".join(c["specialties"])}" data-text="{c["name"].lower()} {c["city"].lower()} {" ".join(c["specialties"]).lower()}"'

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
    return f'<span class="{cls}"><img src="/assets/logos/{sub}/{fn}" alt="Logo de {c["name"]}" loading="lazy"></span>'

def card(c):
    badge = ' <span class="badge">ficha preliminar</span>' if c["status"] == "preliminar" else ""
    extra = (" · " + " · ".join(c["cities_extra"])) if c.get("cities_extra") else ""
    tags = "".join(f'<span class="tag">{s}</span>' for s in c["specialties"])
    return f'''<div class="card" {attrs(c)}>{logo_img(c)}<span class="loc">{c["city"]}{extra} · {c["country"]}</span>
<h3><a href="/clinica/{c["slug"]}/">{c["name"]}</a>{badge}</h3>
<p>{c["summary"][:150]}{"…" if len(c["summary"])>150 else ""}</p>
<div class="tags">{tags}</div></div>'''

# --- index ---
city_chips = "".join(f'<button class="chip" data-f="city" data-v="{ct}">{ct}</button>' for ct in city_order)
country_chips = "".join(f'<button class="chip" data-f="country" data-v="{co}">{co}</button>' for co in countries)
spec_chips = "".join(f'<button class="chip" data-f="spec" data-v="{s}">{s}</button>' for s in specialties)
allcards = "".join(card(c) for c in clinics)

JS = """<script>
(function(){
  var state={city:null,country:null,spec:null,q:""};
  var cards=[].slice.call(document.querySelectorAll(".grid .card"));
  var count=document.getElementById("count");
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
  apply();
})();
</script>"""

INDEX_LD = '<script type="application/ld+json">' + json.dumps({
    "@context": "https://schema.org", "@type": "WebSite", "name": SITE,
    "url": BASE, "description": TAGLINE, "inLanguage": "es",
}, ensure_ascii=False) + "</script>"

index = head(f"{SITE} — {TAGLINE}", "Todos queremos vivir más años con salud. Diuvita te ayuda a encontrar clínica de medicina de longevidad por ciudad, país y especialidad.", "/", INDEX_LD) + f"""
<div class="hero">
<p class="kicker">La guía de las clínicas de longevidad</p>
<h1>Todos queremos vivir más años. La pregunta es <em>dónde empezar</em>.</h1>
<p class="sub">La medicina de la longevidad ya existe: chequeos de edad biológica, biomarcadores, programas de prevención. Diuvita te ayuda a encontrar dónde — sin rankings, sin publicidad, con criterios claros.</p>
<div class="finder" id="buscar">
<input id="q" type="search" placeholder="Busca por nombre, ciudad o especialidad…" aria-label="Buscar clínica">
<div class="fgroup"><span class="flabel">País</span><div class="chips">{country_chips}</div></div>
<div class="fgroup"><span class="flabel">Ciudad</span><div class="chips">{city_chips}</div></div>
<div class="fgroup"><span class="flabel">Superespecialidad</span><div class="chips">{spec_chips}</div></div>
</div>
</div>
<p class="rescount" id="count"></p>
<div class="wrap"><div class="grid">{allcards}</div>
<div class="note">¿Diriges una clínica de longevidad que no aparece aquí? Escríbenos y la evaluaremos según nuestros <a href="/sobre/">criterios de inclusión</a>. Aparecer en Diuvita es gratuito — y no se puede pagar.</div>
</div>{JS}""" + FOOTER

# --- fichas ---
def ficha(c):
    servicios = "".join(f"<li>{s}</li>" for s in c["services"])
    tags = "".join(f'<span class="tag">{s}</span>' for s in c["specialties"])
    tech = f'<h2>Tecnología destacada</h2><p style="color:var(--muted)">{c["tech"]}</p>' if c.get("tech") else ""
    prelim = '<div class="note">Ficha preliminar: elaborada a partir de información pública básica, pendiente de ampliación y verificación detallada.</div>' if c["status"] == "preliminar" else ""
    extra = (" · " + " · ".join(c["cities_extra"])) if c.get("cities_extra") else ""
    ld = '<script type="application/ld+json">' + json.dumps({
        "@context": "https://schema.org", "@type": "MedicalClinic",
        "name": c["name"], "url": c["web"], "address": c["address"],
        "medicalSpecialty": c["specialties"], "description": c["summary"],
    }, ensure_ascii=False) + "</script>"
    return head(f'{c["name"]} — clínica de longevidad en {c["city"]} | {SITE}', c["summary"][:150], f'/clinica/{c["slug"]}/', ld) + f"""
<div class="ficha"><p class="crumbs"><a href="/">Diuvita</a> → <a href="/ciudad/{slugify(c["city"])}/">{c["city"]}</a> → {c["name"]}</p>
{logo_img(c, ficha=True)}<h1>{c["name"]}</h1><p class="loc">{c["city"]}{extra} · {c["country"]} · {c["address"]}</p>
<div class="tags">{tags}</div>
<p class="summary">{c["summary"]}</p>
<h2>Servicios</h2><ul>{servicios}</ul>
{tech}
<a class="visit" href="{c["web"]}" rel="nofollow noopener" target="_blank">Visitar web oficial ↗</a>
{prelim}</div>""" + FOOTER

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
