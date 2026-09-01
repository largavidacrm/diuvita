# Paquetes de decisión de propuestas

`scripts/review_proposal_decision_packets.py` prepara propuestas abiertas de
`review_queue` como unidades pequeñas para revisión humana o asistencia futura
con LLM.

El contrato principal es:

- Un paquete representa una tarjeta abierta y una sola decisión.
- Las acciones posibles son siempre `approve`, `reject` o `modify`.
- `modify` solo puede tocar los campos listados en `editable_fields`.
- Las revisiones manuales de calidad que solo traen un "campo pendiente" pueden
  incluir `manual_review_targets`, que apuntan al campo exacto del admin que
  Daniel debe revisar. Es una ruta de trabajo manual, no un permiso para que el
  LLM invente valores.
- Esas revisiones manuales también pueden incluir `manual_review_context`: un
  resumen seguro con el título legible, el campo del admin, el motivo pendiente
  y el paso humano esperado. Sirve para asistencia futura con LLM sin darle
  permiso para escribir datos ni resolver la tarjeta.
- Cuando una revisión tiene ficha o candidata asociada, el paquete puede incluir
  `manual_profile_edit_context`: lista los campos que Daniel puede corregir con
  **Editar ficha** en el panel izquierdo. Es contexto humano, no amplía
  `editable_fields` ni permite al LLM escribir cambios de perfil por su cuenta.
- Si Daniel aporta una URL oficial desde **Pasar URL al agente**, el paquete
  conserva `source_handoff` y `source_job_request` con alcance
  `primary_target_first`: primero se pide al agente el campo principal de esa
  revisión manual; solo se usan los demás campos pendientes como fallback cuando
  no hay un campo único claro.
- Si Daniel aporta una URL oficial desde una tarjeta de especialistas sin
  fuente clara, la ruta debe conservarse como
  `review_card_specialist_source_handoff` y el alcance como
  `specialist_source_only`. Esa URL solo sirve para preparar una nueva propuesta
  revisable de especialistas.
- Si esa URL ya generó una propuesta revisable, el paquete de esa propuesta
  conserva `source_job_context`: origen aportado por Daniel, campo pedido,
  resumen humano del campo solicitado, alcance, ruta del admin, barrera LLM y
  política de salida. Sin `--include-values`, las URLs completas siguen ocultas.
- Si una propuesta ya trae campos editables pero solo conserva una fuente sin
  contexto, Daniel puede aprobar, rechazar o modificar esos campos manualmente.
  Lo que permanece bloqueado es usar esa fuente como instrucción nueva para el
  LLM hasta recuperar el campo solicitado y el alcance del trabajo.
- Si una propuesta antigua solo trae una fuente pero no conserva contexto de
  trabajo, el paquete expone `source_origin_status:
  "source_without_context"` con el host y el límite LLM: no inferir intención
  original solo por la URL.
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

Para preparar solo tarjetas que no estén marcadas como **fuente sin contexto**:

```bash
python3 scripts/review_proposal_decision_packets.py --llm-ready-only --limit 10
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
- campo manual que abrir si la tarjeta es una revisión manual sin valores
  propuestos.
- contexto manual de campo, motivo y siguiente paso cuando exista.
- contexto de edición manual de la ficha, para recordar qué campos puede
  corregir Daniel sin convertirlos en salida automática del LLM.
- fuente oficial a pedir o usar como trabajo interno, respetando siempre el
  alcance `primary_target_first` si está presente.
- fuente oficial de especialistas cuando el alcance sea
  `specialist_source_only`, sin proponer cambios de otros campos de la ficha.
- contexto del trabajo de fuente que produjo la propuesta, para saber si nació
  de una URL aportada por Daniel y qué campo debía resolver primero.
- estado de origen de la fuente, distinguiendo entre contexto recuperable y
  fuente sin contexto para no convertir una URL útil en permiso implícito.
- estado estructurado de Google Maps cuando la propuesta trae ese campo,
  recordando que incluso un enlace con pinta de perfil directo requiere
  comprobación humana antes de aprobar.
- estado estructurado de Valoraciones Google cuando la propuesta trae ese
  enlace, recordando que debe pertenecer a la misma ficha principal de Google
  Maps antes de guardarse. El paquete incluye una `approval_dependency` que
  indica si ya existe un perfil Google Maps directo en la ficha o en la misma
  propuesta; si no existe, una sugerencia LLM de aprobar o modificar
  Valoraciones Google debe rechazarse en validación.

El LLM no debe:

- inventar campos fuera de `editable_fields`;
- inventar datos para un `manual_review_target`;
- convertir `manual_profile_edit_context` en cambios de ficha automáticos;
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
- no introduce claves fuera del esquema permitido;
- no trae escrituras, publicación, Supabase, Netlify ni SQL;
- no modifica campos fuera de `editable_fields`;
- permite `modify` sin `field_changes` solo si apunta a un
  `manual_review_target_key` permitido;
- devuelve el objetivo manual validado con su `admin_target_id`, para que la UI
  o una futura capa LLM pueda abrir el campo correcto sin adivinar;
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
Por defecto limpia valores crudos aunque el paquete de entrada los trajera, pero
mantiene el resumen seguro del campo que Daniel pidió revisar y la barrera LLM
del trabajo de fuente.

Para usos automatizados, añade `--require-llm-ready`: si la tarjeta es solo
fuente sin contexto de tarea, el preparador se detiene y pide revisión manual
en vez de generar un prompt ambiguo.

Antes de preparar un lote asistido, usa el preflight:

```bash
python3 scripts/review_llm_batch_preflight.py --compact --limit 20
```

Este informe no llama a ningún LLM y no escribe datos. Solo indica qué tarjetas
pasarían el modo estricto, cuáles quedan bloqueadas por **fuente sin contexto**
y qué revisiones manuales tienen un campo concreto para abrir en el admin. Sin
`--compact`, devuelve JSON para automatizaciones internas.
Las revisiones manuales con campo claro pueden aparecer como **ruta manual
lista**: eso solo permite preparar una ayuda de navegación hacia el campo, no
rellenar valores ni publicar datos.
Para quedarse solo con tarjetas estrictamente preparables:

```bash
python3 scripts/review_llm_batch_preflight.py --llm-ready-only --limit 20
```

Para una preparación local deliberada con valores completos:

```bash
python3 scripts/prepare_review_decision_llm_prompt.py \
  --packet-file packet.json \
  --allow-full-values
```

Para auditar si las propuestas antiguas conservan el contexto del trabajo de
fuente que las originó:

```bash
python3 scripts/audit_review_source_job_context.py --compact
```

Este auditor es de solo lectura: ayuda a decidir si una tarjeta ya está lista
para asistencia LLM, si el contexto se puede recuperar desde `agent_jobs`, o si
debe tratarse como revisión manual sin inferir intención original. La salida
humana usa etiquetas como **listo para LLM**, **recuperable desde trabajo** y
**solo revisión manual**.

## Relación con el panel

El panel `/admin/` mantiene la experiencia humana simple:

```text
abrir propuesta -> revisar ese cambio -> aprobar / rechazar / modificar -> volver a lista
```

Los paquetes de decisión son la forma técnica de conservar esa misma estructura
para futuras automatizaciones sin volver a agrupar varias decisiones en una
misma ficha.
