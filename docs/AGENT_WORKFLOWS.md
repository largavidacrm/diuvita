# Vitalarga agent workflows

This document defines the first agent-ready workflows. It intentionally starts narrow: clinics only.

Operational boundary: every workflow in this document is subordinate to
`docs/VITALARGA_LIMITES_OPERATIVOS.md`. If a job, review, extraction or publishing
step touches a hard limit, it must stop and escalate to Daniel using that guide's
format before acting.

## Shared job lifecycle

Every workflow uses `public.agent_jobs`.

```text
queued -> running -> completed
queued -> running -> failed -> queued
queued -> running -> failed -> dead_letter
queued -> running -> completed + requires_human
```

Every job stores:

- `job_type`
- `status`
- `priority`
- `clinic_id` or generic `entity_id`
- `input`
- `output`
- `confidence`
- `attempts`
- `error_message`
- `model_tier`
- `cost_cents`

## DISCOVER_CLINIC

Purpose: find a clinic Vitalarga does not already know about.

Input:

```json
{
  "country": "Espana",
  "query": "longevity clinic Madrid",
  "max_results": 20
}
```

Output:

```json
{
  "candidates": [
    {
      "name": "Example Clinic",
      "website": "https://example.com",
      "city": "Madrid",
      "country": "Espana",
      "discovery_confidence": 0.91,
      "source_url": "https://example.com"
    }
  ]
}
```

Rules:

- Never publish from discovery.
- Store candidates as jobs or draft clinic records.
- Anything with low clinic probability goes to review or is discarded.

## DEDUPE_CLINIC

Purpose: decide whether a candidate is new, duplicate or ambiguous.

Signals:

- Domain match.
- Name similarity.
- Address similarity.
- Phone/email match.
- Medical director/team overlap.
- Embedding similarity once pgvector is active.

Rules:

- `duplicate_probability >= 0.90`: propose merge.
- `duplicate_probability <= 0.20`: treat as new candidate.
- Anything between: create a review item.

## EXTRACT_CLINIC_PROFILE

Purpose: convert web evidence into structured facts.

Output goes into `field_claims`, not directly into published clinic data.

Operator bridge:

- A review card can create a bounded `EXTRACT_CLINIC_PROFILE` job with
  `source_url`, `clinic_slug`, `from_review_id`, `requested_fields`,
  `requested_field_labels`, `primary_requested_fields`,
  `primary_requested_field_labels`, `human_supplied_source`,
  `operator_intent`, `operator_requested_field_summary`, `llm_boundary`,
  `target_scope`, `ui_route` and an `allowed_output` of
  `review_queue_proposal_only`.
- Those jobs are queued by the admin UI and processed only by the supervised
  CTO cycle or an explicit worker run. Refreshing the dashboard never executes
  them, and the UI should say they are waiting for the supervised cycle.
- When the source is supplied from a manual-review field banner, the job should
  carry `target_scope: "primary_target_first"` and `ui_route:
  "manual_review_banner_source_handoff"` so the worker/LLM treats Daniel's URL
  as evidence for the active field first, not as permission to fill every gap in
  the ficha.
- When Daniel supplies an official team/specialist URL from a specialist review
  card that has proposed professionals but no clear source, the job should carry
  `target_scope: "specialist_source_only"` and `ui_route:
  "review_card_specialist_source_handoff"`. The worker/LLM may use that URL only
  to prepare a new specialist-focused review proposal; it must not treat the URL
  as approval to publish or to broaden the card into unrelated fields.
- `scripts/process_extract_clinic_profile_jobs.py` can process those jobs in
  shadow mode and turn clear findings into a `clinic_profile_enrichment` review
  card.
- If that created or refreshed card contains actionable proposed data for the
  same source, the worker resolves the original review as superseded. That is a
  queue-management action only: it does not approve, publish or save clinic
  profile fields.
- The processor filters proposed fields to the job's `requested_fields`; it does
  not use a useful source as permission to propose unrelated clinic changes.
- The generated review card must preserve the job's primary-field scope
  metadata (`primary_requested_fields`, `primary_requested_field_labels`,
  `target_scope`, `ui_route`) so the next human or LLM step can see why the URL
  was supplied.
- If the URL comes from an open manual-review card, the admin resolves that
  origin card immediately as source-sent so Daniel returns to the list while the
  worker runs. When the worker creates or refreshes the concrete enrichment
  proposal, the new proposal keeps all source/job context for future
  LLM-assisted review.
- Decision packets for those generated cards expose the same provenance as
  `source_job_context`, redacting full URLs by default and keeping the allowed
  output as review-proposal-only.
- `scripts/audit_review_source_job_context.py` can read open enrichment cards
  and report which ones already have that context, which can recover it from
  the originating `agent_jobs` row, and which should remain purely manual.
- Human-supplied URLs are treated as evidence pointers, not approvals. They can
  guide the future LLM/worker, but the only allowed output is a new review
  proposal.
- Completing the job never edits a clinic profile, never publishes and never
  bypasses Daniel's approve/reject/modify decision.

Required for each claim:

- `field_path`
- `value`
- `source_record_id`
- `agent_name`
- `agent_version`
- `confidence`

Examples of field paths:

- `identity.canonical_name`
- `location.address`
- `contact.email`
- `services.diagnostics.vo2max`
- `services.treatments.ihht`
- `pricing.initial_consultation`
- `team.medical_director`

## VERIFY_CLINIC_PROFILE

Purpose: adversarial verification.

The verifier does not improve the extractor's answer. It challenges each important claim independently.

Verdicts:

- `accepted`
- `rejected`
- `stale`
- `conflict`
- `review`

Medical claims, physician credentials and prices need stronger verification than address/contact fields.

## PREPARE_REVIEW_DECISION_PACKET

Purpose: turn one open `review_queue` card into the exact information needed
for a human decision or future LLM-assisted preparation.

Detailed contract: `docs/REVIEW_DECISION_PACKETS.md`.

Required behavior:

- One packet represents one review card and one decision.
- Include the affected clinic, proposal type, current relevant fields, proposed
  fields, evidence and essential warnings.
- Include the packet schema version, allowed actions and `editable_fields` so
  automated preparation cannot introduce unrelated clinic changes.
- When the review has an associated clinic or candidate, include
  `manual_profile_edit_context` for the **Editar ficha** side panel. This is
  human-only context: it documents which clinic fields Daniel can correct while
  reviewing, but it must not expand `editable_fields` or allow LLM writes.
- For quality-audit cards with no proposed values, include
  `manual_review_targets` and, when useful, a bounded `source_job_request`.
  This lets a future LLM suggest the exact manual field or official source job
  without inventing clinic data.
- If `source_job_request.target_scope` is `primary_target_first`, the LLM should
  keep its help focused on the packet's primary manual target and should not
  broaden the job unless the packet has no unique primary target.
- Default output must be safe: no raw proposed values or full evidence URLs.
- Full values are allowed only with an explicit local operator flag for
  assisted preparation.
- Never approve, reject, resolve, edit clinics or publish pages.
- LLM output may suggest or organize the decision, but the card remains
  reviewable and Daniel's action is still `approve`, `reject` or `modify`.
- `modify` may only change fields listed in that packet's `editable_fields`.
- `manual_profile_edit_context` can be used to explain that Daniel has manual
  profile-edit controls in the side panel; it is not a source of automatic
  `field_changes`.
- If `editable_fields` is empty, `modify` is valid only as a manual-review
  route to one of the packet's `manual_review_targets`; it must not carry
  invented `field_changes`.
- Future LLM suggestions must pass
  `scripts/validate_review_decision_suggestion.py` before they are shown or
  transformed into any review UI state.
- Future LLM prompts should be generated through
  `scripts/prepare_review_decision_llm_prompt.py` so prompt wording, expected
  JSON schema and validation requirements stay consistent.
- If a packet contains `source_job_context`, the LLM can use it only to explain
  provenance and keep attention on the requested field; it is not permission to
  write source data, publish, or broaden the proposal.
- If a packet contains `source_origin_status: source_without_context`, the LLM
  may treat the URL as evidence to review, but must not infer the operator's
  original intent from the host or URL alone.
- If a packet contains `google_reviews_review.approval_dependency` and
  `satisfied` is false, the LLM must not suggest approving or modifying the
  Google reviews field until the clinic has a confirmed Google Maps profile or
  the same packet also proposes one for Daniel to confirm first.
- `scripts/manual_review_route_brief.py` summarizes open review packets into
  operator routes without writing data or calling an LLM. It is used to separate
  cards that should open a manual admin field, cards that can accept an official
  source URL for a bounded agent job, source-only cards that are still
  reviewable by Daniel because they already contain editable proposed fields,
  cards that are blocked for LLM help by missing source context, and direct
  one-change proposals.
- `scripts/run_cto_shadow_cycle.py` includes that route brief as a read-only
  step, so unattended CTO summaries preserve the manual/LLM handoff path
  without creating cards or changing clinic data.

## APPLY_PUBLICATION_RULES

Purpose: deterministic arbiter.

Rules examples:

- Accepted address/contact fields can update draft data when confidence is high.
- Treatment claims need explicit source support.
- Price claims with stale sources can be stored but marked stale.
- Any conflict with `human_overrides.locked = true` creates review and does not overwrite.
- Any rejected claim remains stored for audit but is not published.

## PUBLISH_CANDIDATE

Purpose: update the canonical record after rules pass.

Required side effects:

- Write `entity_versions`.
- Write `change_events`.
- Update `clinics.current_data`.
- Trigger static-site regeneration or future API cache refresh.

Early mode:

- Shadow only.
- Produce proposed output but do not update public pages.

## REVIEW_CLINIC_CLAIM_REQUEST

Purpose: route clinic-profile claim requests to Daniel as a human decision.

Required behavior:

- Create or show a `clinic_claim_request` review card for the requested clinic.
- Do not verify identity automatically.
- Do not grant account access automatically.
- Do not edit clinic data automatically.
- Do not publish any profile change from the claim request alone.
- If Daniel approves the review card, store requester details only as
  `clinics.current_data.internal_contact` with internal visibility. This is an
  operational contact, not a public profile change and not an access grant.
- Keep the card open until Daniel decides whether to request proof, accept the
  claim operationally or close it.

## NOTIFY_DIGEST

Purpose: avoid noisy notifications.

Daily digest should include:

- Clinics discovered.
- Clinics proposed.
- Duplicates detected.
- Fields updated.
- Review items created.
- Failed jobs.
- Estimated AI cost.

Individual notifications should be reserved for failures, data conflicts or high-value decisions.
