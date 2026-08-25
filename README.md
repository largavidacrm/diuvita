# Diuvita — la guía de las clínicas de longevidad

Sitio estático: `data/clinics.json` + `data/posts/*.md` → `python3 build.py` → `dist/`.
Deploy: Netlify (build automático en cada push, ver `netlify.toml`).
Las fichas nuevas esperan validación humana en `pendientes/` antes de entrar en `data/clinics.json`.
