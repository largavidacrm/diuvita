#!/usr/bin/env python3
"""Checks that admin review actions keep their context after closing panels."""
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    index = (ROOT / "admin" / "index.html").read_text(encoding="utf-8")
    match = re.search(r"async function dismissReview\(\) \{([\s\S]+?)\n    \}", index)
    check(match is not None, "dismissReview function missing")
    body = match.group(1)

    check(
        "var reviewType = activeReview.review_type;" in body,
        "dismissReview should keep review type before closing",
    )
    check(
        'var note = trimmed("reviewResolutionNote") || defaultDismissNote(reviewType);' in body,
        "dismissReview should keep the resolution note before closing",
    )
    check("p_note: note" in body, "dismissReview should submit the preserved note")

    after_close = body.split("closeReviewEditor();", 1)[-1]
    check(
        "activeReview.review_type" not in after_close,
        "dismissReview should not read activeReview after closeReviewEditor",
    )
    check(
        "function candidateReviewSources" in index
        and "candidate.source_urls" in index
        and 'setLinks("reviewCandidateSource", candidateReviewSources(candidate, payload, source));' in index,
        "candidate reviews should show all source URLs",
    )
    check(
        'id="reviewProposedLinksBlock"' in index
        and 'id="reviewCandidateProposedLinks"' in index
        and "function proposalLinkUrl(value)" in index
        and "function proposalLinkItems(payload)" in index
        and "function proposalLinkWarning(item)" in index
        and "function setProposedLinks(payload)" in index
        and "setProposedLinks(payload);" in index,
        "review editor should show proposed links separately",
    )
    check(
        'id="reviewContextPanel"' in index
        and 'id="reviewContextTitle"' in index
        and 'id="reviewContextDetail"' in index
        and "function reviewContextCopy" in index
        and "function renderReviewContext" in index
        and "renderReviewContext(activeReview, payload, blocksDraft);" in index,
        "review editor should show publication context for every review card",
    )
    check(
        "Candidata: todavía no está en la guía." in index
        and "Sus datos no aparecerán online hasta crear un borrador" in index
        and "especialistas propuestos" in index
        and "Mejora de ficha existente." in index
        and "La información está recogida como propuesta interna" in index,
        "candidate and enrichment review context should explain why data is not public yet",
    )
    check(
        'return /^https?:\\/\\//i.test(clean) ? clean : "";' in index
        and '["maps_url", "Google Maps", "maps_url"]' in index
        and '["google_reviews_url", "Valoraciones Google", "google_reviews_url"]' in index
        and '["reviews_url", "Valoraciones Google", "google_reviews_url"]' in index
        and '["pricing_url", "Página de precios", "pricing_url"]' in index,
        "proposed review links should be safe and cover Maps/reviews/pricing",
    )
    check(
        "parece búsqueda, ruta o dirección" in index
        and "falta señal clara de ficha de clínica" in index
        and '" · sede principal"' in index
        and '" · sede adicional"' in index,
        "proposed Google Maps links should warn on weak URLs without numbered sede labels",
    )
    check(
        'data-load-related-proposals' in index
        and "Cargar mejoras juntas" in index
        and "function mergeReviewPayloads(rows)" in index
        and "function loadRelatedEnrichmentProposals()" in index
        and "activeClinicReviewIds" in index,
        "related enrichment reviews should be loadable as one grouped proposal",
    )
    check(
        "Ficha actualizada desde propuestas agrupadas." in index
        and "alguna tarjeta no se cerró automáticamente" in index
        and "Conflicto en " in index,
        "saving grouped proposals should resolve grouped cards and warn on conflicts",
    )
    css = (ROOT / "admin" / "admin.css").read_text(encoding="utf-8")
    check(".review-context" in css, "review context should be styled")
    check(".compact-list small" in css, "proposed link URLs should remain readable on mobile")
    check(".compact-list em" in css, "proposed link warnings should be styled")
    check("quick-primary" in index and "quick-action" in index, "quick review actions should be classified")
    check(".review-action-strip .quick-primary" in css, "primary quick action should be styled")
    check("grid-template-columns: minmax(220px, 1.35fr) repeat(3, minmax(140px, 1fr))" in css, "quick actions should use a stable grid")
    check("grid-template-columns: 1fr" in css, "quick actions should stack on mobile")
    print("OK admin review actions: dismiss keeps context")


if __name__ == "__main__":
    main()
