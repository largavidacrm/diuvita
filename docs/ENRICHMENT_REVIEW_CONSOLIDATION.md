# Consolidacion de mejoras duplicadas

`scripts/consolidate_profile_enrichment_reviews.py` revisa tarjetas abiertas de
tipo `clinic_profile_enrichment` y agrupa las que pertenecen a la misma clinica.

Objetivo: que Daniel pueda trabajar una ficha como un solo caso, en vez de
abrir varias propuestas separadas con campos repetidos.

## Seguridad

- Es de solo lectura.
- No edita `clinics`.
- No resuelve ni descarta tarjetas de `review_queue`.
- No publica la web.
- No imprime credenciales.

## Uso

```bash
python3 scripts/consolidate_profile_enrichment_reviews.py
```

Salida JSON para ciclos internos:

```bash
python3 scripts/consolidate_profile_enrichment_reviews.py --json
```

Enfocar una clinica:

```bash
python3 scripts/consolidate_profile_enrichment_reviews.py --clinic Sensabell
```

## Que mira

- Cuantas tarjetas de mejora tiene abierta una misma clinica.
- Que campos se pueden fusionar.
- Que fuentes distintas apoyan el grupo.
- Que campos ya parecen estar en la ficha actual.
- Que campos escalares tienen conflicto, por ejemplo dos telefonos principales
  distintos.
- Que telefonos no parecen numeros espanoles plausibles, para evitar que una
  colegiacion o un identificador con guiones se guarde como contacto.
- Que propuestas traen varios telefonos espanoles claros en un solo campo; en
  ese caso los separa como telefono principal/fijo/movil para revision humana.

## Resultado esperado

Si no hay conflictos, el siguiente paso humano normal es abrir el caso en
`/admin/` y usar **Cargar mejoras juntas**.

Si hay conflictos, Daniel debe comparar las fuentes antes de guardar la ficha.

Si el informe separa telefonos, Daniel debe revisar que cada numero corresponde
a la clinica antes de guardar. La separacion no publica ni aprueba el dato por
si sola.
