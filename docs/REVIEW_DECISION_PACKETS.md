# Paquetes de decisión de propuestas

`scripts/review_proposal_decision_packets.py` prepara propuestas abiertas de
`review_queue` como unidades pequeñas para revisión humana o asistencia futura
con LLM.

El contrato principal es:

- Un paquete representa una tarjeta abierta y una sola decisión.
- Las acciones posibles son siempre `approve`, `reject` o `modify`.
- `modify` solo puede tocar los campos listados en `editable_fields`.
- Las auditorías de calidad que solo traen un "campo pendiente" pueden incluir
  `manual_review_targets`, que apuntan al campo exacto del admin que Daniel debe
  revisar. Es una ruta de trabajo manual, no un permiso para que el LLM invente
  valores.
- La salida por defecto no incluye valores completos, emails, teléfonos crudos
  ni URLs completas de evidencia.
- El script no resuelve tarjetas, no edita clínicas y no publica páginas.

## Uso seguro

Para ver paquetes sin valores completos:

```bash
python3 scripts/review_proposal_decision_packets.py --limit 10
```

Para centrarlo en una clínica o fragmento de título:

```bash
python3 scripts/review_proposal_decision_packets.py --clinic IMDA --limit 5
```

Para preparar una decisión local con valores completos:

```bash
python3 scripts/review_proposal_decision_packets.py --review-id REVIEW_ID --include-values
```

`--include-values` es solo para preparación local deliberada. No debe usarse en
resúmenes largos, logs compartidos, prompts externos o documentación.

## Uso con LLM

Un LLM puede recibir un paquete y devolver una ayuda breve:

- decisión sugerida;
- motivo;
- advertencias que Daniel debe mirar;
- propuesta corregida si la acción sugerida es `modify`.
- campo manual que abrir si la tarjeta es una auditoría sin valores propuestos.

El LLM no debe:

- inventar campos fuera de `editable_fields`;
- inventar datos para un `manual_review_target`;
- convertir una advertencia en aprobación automática;
- resolver la tarjeta;
- ejecutar escrituras en Supabase;
- cambiar publicación, estado público o datos sensibles;
- sustituir la revisión humana de Daniel.

Si el paquete incluye Google Maps, especialistas, precios, colegiación visible o
una reclamación de ficha, el resultado debe seguir marcado como revisión humana
obligatoria.

Antes de enseñar o usar una sugerencia de LLM, pásala por el validador local:

```bash
python3 scripts/validate_review_decision_suggestion.py \
  --packet-file packet.json \
  --suggestion-file suggestion.json
```

El validador no se conecta a Supabase y no escribe datos. Solo comprueba que la
sugerencia:

- usa una acción permitida;
- corresponde a la misma tarjeta;
- no trae escrituras, publicación, Supabase, Netlify ni SQL;
- no modifica campos fuera de `editable_fields`;
- permite `modify` sin `field_changes` solo si apunta a un
  `manual_review_target_key` permitido;
- rechaza modificaciones con Google Maps débil o teléfono dudoso;
- mantiene la decisión final como revisión humana.

Por defecto también oculta valores crudos de la sugerencia. Para depuración
local deliberada:

```bash
python3 scripts/validate_review_decision_suggestion.py \
  --packet-file packet.json \
  --suggestion-file suggestion.json \
  --include-values
```

Para preparar el prompt estándar que recibirá el LLM:

```bash
python3 scripts/prepare_review_decision_llm_prompt.py \
  --packet-file packet.json
```

El preparador devuelve mensajes, esquema esperado y referencia al validador.
Por defecto limpia valores crudos aunque el paquete de entrada los trajera.
Para una preparación local deliberada con valores completos:

```bash
python3 scripts/prepare_review_decision_llm_prompt.py \
  --packet-file packet.json \
  --allow-full-values
```

## Relación con el panel

El panel `/admin/` mantiene la experiencia humana simple:

```text
abrir propuesta -> revisar ese cambio -> aprobar / rechazar / modificar -> siguiente
```

Los paquetes de decisión son la forma técnica de conservar esa misma estructura
para futuras automatizaciones sin volver a agrupar varias decisiones en una
misma ficha.
