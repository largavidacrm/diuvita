# -*- coding: utf-8 -*-
"""Descarga los logos candidatos de data/logos.json y genera miniaturas.
Se ejecuta en GitHub Actions (con red completa). Resultados en assets/logos/.
"""
import json, os, io, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG = os.path.join(ROOT, "assets", "logos", "orig")
THUMB = os.path.join(ROOT, "assets", "logos", "thumb")
os.makedirs(ORIG, exist_ok=True)
os.makedirs(THUMB, exist_ok=True)

logos = json.load(open(os.path.join(ROOT, "data", "logos.json"), encoding="utf-8"))
status = {}

def ext_for(url, ctype):
    for e in (".svg", ".webp", ".png", ".jpg", ".jpeg"):
        if url.lower().split("?")[0].endswith(e):
            return e
    if "svg" in ctype: return ".svg"
    if "webp" in ctype: return ".webp"
    if "jpeg" in ctype or "jpg" in ctype: return ".jpg"
    return ".png"

for slug, info in logos.items():
    url = info["url"]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; DiuvitaBot/1.0; +https://diuvita.com)"})
        resp = urllib.request.urlopen(req, timeout=20)
        data = resp.read()
        ctype = resp.headers.get("Content-Type", "")
    except Exception as e:
        status[slug] = {"ok": False, "error": str(e)[:120]}
        continue
    ext = ext_for(url, ctype)
    with open(os.path.join(ORIG, slug + ext), "wb") as f:
        f.write(data)
    if ext == ".svg":
        with open(os.path.join(THUMB, slug + ".svg"), "wb") as f:
            f.write(data)
        status[slug] = {"ok": True, "orig": slug + ext, "thumb": slug + ".svg", "bytes": len(data)}
        continue
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(data)).convert("RGBA")
        im.thumbnail((260, 64))
        buf = io.BytesIO()
        im.save(buf, format="PNG", optimize=True)
        with open(os.path.join(THUMB, slug + ".png"), "wb") as f:
            f.write(buf.getvalue())
        status[slug] = {"ok": True, "orig": slug + ext, "thumb": slug + ".png", "bytes": len(data)}
    except Exception as e:
        status[slug] = {"ok": True, "orig": slug + ext, "thumb": None, "error": "thumb: " + str(e)[:100]}

with open(os.path.join(ROOT, "assets", "logos", "status.json"), "w", encoding="utf-8") as f:
    json.dump(status, f, ensure_ascii=False, indent=2)
print(json.dumps(status, indent=2)[:2000])
