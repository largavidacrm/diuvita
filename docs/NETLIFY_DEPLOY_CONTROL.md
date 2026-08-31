# Netlify deploy control

Vitalarga debe evitar publicaciones pequeñas a produccion cuando el cambio no
afecta lo que ve el publico o el panel interno.

## Politica operativa

- Agrupar cambios tecnicos y subirlos a `main` en tandas.
- Usar pruebas locales antes de subir, para no gastar publicaciones en errores.
- Saltar builds de Netlify cuando solo cambien docs, scripts internos,
  migraciones Supabase o material pendiente privado.
- Mantener build obligatorio cuando cambien la web publica, el admin, datos,
  logos, posts, `build.py` o `netlify.toml`.

## Regla automatica

`netlify.toml` usa:

```toml
[build]
  ignore = "python3 ./scripts/netlify_ignore_build.py"
```

Netlify interpreta el resultado asi:

- salida `0`: no construir;
- salida `1`: construir.

El script es conservador. Si no entiende un archivo, prefiere construir.

## Limite importante

El `ignore` de Netlify no cancela builds disparados por un build hook. En
Vitalarga existe un hook privado desde Supabase para reconstruir la web cuando una
ficha publicable cambia.

Para reducir esos costes tambien, la siguiente mejora recomendada es cambiar el
admin a "publicacion por lote": Daniel puede editar varias clinicas y luego
pedir una sola publicacion web al final de la sesion.

La migracion `supabase/migrations/0018_batch_public_site_rebuilds.sql` deja una
primera version preparada: agrupa las reconstrucciones pedidas desde Supabase en
ventanas de 30 minutos, configurable con `vitalarga_rebuild_batch_minutes`.

La migracion `supabase/migrations/0023_public_site_rebuild_pending_control.sql`
mejora ese control: registra por separado el ultimo cambio guardado y la ultima
peticion enviada a Netlify. Asi el admin puede mostrar **cambios pendientes de
verse online** y ofrecer el boton **Actualizar web ahora** para lanzar una sola
publicacion manual al final de un lote de ediciones.

Ese boton no cambia datos de clinicas. Solo pide a Netlify que reconstruya la
web publica con los datos ya guardados y visibles segun su estado.

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

Esta comprobacion no muestra el build hook privado, solo si existe, si la
ventana esta configurada y si la funcion de Supabase ya usa esa ventana.

El panel `/admin/` tambien muestra este estado en **Plan global** y en
**Estado del sistema** como **Publicación agrupada**.
