# Consolidacion de mejoras duplicadas

`scripts/consolidate_profile_enrichment_reviews.py` revisa tarjetas abiertas de
tipo `clinic_profile_enrichment` y agrupa las que pertenecen a la misma clinica.

Objetivo: que el sistema detecte repeticion, conflictos y campos claros antes de
que Daniel revise. La decision humana en el panel sigue siendo una tarjeta cada
vez.

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
python3 scripts/consolidate_profile_enrichment_reviews.py --clinic "Nombre de la clinica"
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
- En que orden conviene revisar los campos del grupo, priorizando conflictos,
  telefonos dudosos, Maps/valoraciones y despues el resto de datos.

## Resultado esperado

Si no hay conflictos, el siguiente paso humano normal es abrir el grupo en
`/admin/` y resolver una propuesta cada vez.

Si hay conflictos, Daniel debe comparar las fuentes antes de aprobar la
propuesta afectada.

Si el informe separa telefonos, Daniel debe revisar que cada numero corresponde
a la clinica antes de aprobar. La separacion no publica ni aprueba el dato por
si sola.

La linea **orden sugerido** no agrupa decisiones en el admin: solo ayuda a
preparar el trabajo. La validacion real sigue siendo abrir una tarjeta, revisar
un cambio y aprobar, rechazar o modificar.
