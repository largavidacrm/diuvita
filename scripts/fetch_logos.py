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

def looks_like_image(data, ext, ctype):
    head = data[:512].lstrip().lower()
    lower_ctype = (ctype or "").lower()
    if not data or "text/html" in lower_ctype:
        return False
    if head.startswith((b"<!doctype", b"<html")) or b"<meta http-equiv" in head[:300]:
        return False
    if ext == ".svg" and b"<svg" not in head:
        return False
    return True

for slug, info in logos.items():
    if not info.get("aprobado"):
        status[slug] = {"ok": False, "skipped": "no aprobado"}
        continue
    url = info["url"]
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "image/avif,image/webp,image/svg+xml,image/*,*/*;q=0.8",
            "Referer": url.split("/wp-content")[0] + "/" if "/wp-content" in url else url,
        })
        resp = urllib.request.urlopen(req, timeout=20)
        data = resp.read()
        ctype = resp.headers.get("Content-Type", "")
    except Exception as e:
        status[slug] = {"ok": False, "error": str(e)[:120]}
        continue
    ext = ext_for(url, ctype)
    if not looks_like_image(data, ext, ctype):
        status[slug] = {"ok": False, "error": "descarga no válida: no parece un logo"}
        continue
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
