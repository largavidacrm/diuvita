# Reconciliacion de especialistas

`scripts/specialist_review_reconciliation.py` revisa, en modo solo lectura, los
especialistas publicados o propuestos para fichas visibles.

## Seguridad

- No edita `clinics`.
- No resuelve tarjetas de `review_queue`.
- No publica datos de equipo.
- No crea trabajos nuevos.
- El campo `safe_to_auto_publish` queda siempre en `false` para decisiones de
  especialistas.

## Uso

Salida completa para trabajo local:

```bash
python3 scripts/specialist_review_reconciliation.py --clinic "Tiara Health"
```

Salida compacta sin nombres ni URLs:

```bash
python3 scripts/specialist_review_reconciliation.py --clinic "Tiara Health" --compact
```

Salida JSON para ciclos internos o futura ayuda LLM:

```bash
python3 scripts/specialist_review_reconciliation.py --json
```

## Que mira

- Nombres ya publicados en la ficha.
- Nombres propuestos en tarjetas abiertas.
- Nombres detectados en evidencias internas.
- Si cada tarjeta trae fuente clara.
- Nombres nuevos frente a nombres ya representados.
- Decisiones manuales pendientes por tarjeta.

## Resultado esperado

Cada entrada de `manual_decision_items` indica el campo, la tarjeta, si hay
fuente y la accion segura para Daniel. Sirve para preparar la revision, pero la
decision real sigue siendo abrir una tarjeta en el admin, revisar la fuente
publica y aprobar, rechazar o modificar sin publicar automaticamente.
