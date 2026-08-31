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
  `requested_field_labels`, `human_supplied_source`, `operator_intent` and an
  `allowed_output` of `review_queue_proposal_only`.
- `scripts/process_extract_clinic_profile_jobs.py` can process those jobs in
  shadow mode and turn clear findings into a `clinic_profile_enrichment` review
  card.
- The processor filters proposed fields to the job's `requested_fields`; it does
  not use a useful source as permission to propose unrelated clinic changes.
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
- For quality-audit cards with no proposed values, include
  `manual_review_targets` and, when useful, a bounded `source_job_request`.
  This lets a future LLM suggest the exact manual field or official source job
  without inventing clinic data.
- Default output must be safe: no raw proposed values or full evidence URLs.
- Full values are allowed only with an explicit local operator flag for
  assisted preparation.
- Never approve, reject, resolve, edit clinics or publish pages.
- LLM output may suggest or organize the decision, but the card remains
  reviewable and Daniel's action is still `approve`, `reject` or `modify`.
- `modify` may only change fields listed in that packet's `editable_fields`.
- If `editable_fields` is empty, `modify` is valid only as a manual-review
  route to one of the packet's `manual_review_targets`; it must not carry
  invented `field_changes`.
- Future LLM suggestions must pass
  `scripts/validate_review_decision_suggestion.py` before they are shown or
  transformed into any review UI state.
- Future LLM prompts should be generated through
  `scripts/prepare_review_decision_llm_prompt.py` so prompt wording, expected
  JSON schema and validation requirements stay consistent.

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
