# Control de costes de publicación en Netlify

Vitalarga debe evitar publicaciones pequeñas a producción. En el plan actual de
Netlify cada deploy de producción consume créditos, mientras que los Deploy
Previews y branch deploys permiten revisar cambios sin consumir créditos de
producción.

## Política operativa

- Trabajar en ramas y revisar mediante Deploy Previews.
- Agrupar cambios técnicos y subirlos a `main` en una sola tanda coherente.
- Evitar pushes intermedios a `main`; cada publicación debe corresponder a una
  versión que realmente queremos hacer visible.
- Usar pruebas locales antes de subir, para no gastar publicaciones en errores.
- Saltar builds de Netlify cuando solo cambien docs, scripts internos,
  migraciones Supabase o material pendiente privado.
- Mantener build obligatorio cuando cambien la web publica, el admin, datos,
  logos, posts, `build.py` o `netlify.toml`.

## Regla automática para Git

`netlify.toml` usa:

```toml
[build]
  ignore = "python3 ./scripts/netlify_ignore_build.py"
```

Netlify interpreta el resultado asi:

- salida `0`: no construir;
- salida `1`: construir.

El script es conservador. Si no entiende un archivo, prefiere construir.

## Publicación manual desde Supabase

El `ignore` de Netlify no cancela builds disparados por un build hook. En
Vitalarga existe un hook privado desde Supabase para reconstruir la web estática
con los datos ya guardados.

La migración `supabase/migrations/0026_manual_public_site_deploys.sql` convierte
ese flujo en publicación manual:

- Guardar una clínica publicada o preliminar solo marca que hay cambios
  pendientes.
- El trigger de clínicas no llama a Netlify.
- Daniel puede editar varias fichas durante una sesión.
- Solo **Actualizar web ahora** llama al build hook y consume una publicación de
  producción.

Las migraciones anteriores de ventana de 30 minutos se conservan en el historial,
pero `0026` las sustituye como política efectiva. El panel sigue registrando por
separado el último cambio guardado y la última petición enviada a Netlify.

Ese botón no cambia datos de clínicas. Solo pide a Netlify que reconstruya la
web pública con los datos ya guardados y visibles según su estado.

## Presupuesto operativo

- Desarrollo y revisión: ramas y Deploy Previews.
- Producción desde Git: una publicación por lote, no una por commit intermedio.
- Cambios editoriales desde Supabase: una publicación manual al terminar la
  sesión.
- Objetivo inicial: no más de 15 publicaciones de producción al mes para
  Vitalarga salvo incidencia urgente.

## Comprobacion local

```bash
python3 scripts/test_netlify_ignore_build.py
```

Ejemplos:

```bash
python3 scripts/netlify_ignore_build.py --files docs/CTO_ROADMAP.md scripts/admin_digest.py
python3 scripts/netlify_ignore_build.py --files admin/index.html
```

## Comprobacion en Supabase

```bash
scripts/check_supabase_rebuild_batching.sh
```

Esta comprobación no muestra el build hook privado. Confirma si existe, si el
modo es manual, si los cambios automáticos solo quedan pendientes y si el botón
de administración conserva la única llamada autorizada a Netlify.

El panel `/admin/` también muestra este estado en **Plan global** y en
**Estado del sistema** como **Publicación web: Manual**.
