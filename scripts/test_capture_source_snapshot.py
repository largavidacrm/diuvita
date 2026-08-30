#!/usr/bin/env python3
"""Basic checks for compact source snapshots."""
import urllib.error

import capture_source_snapshot
from capture_source_snapshot import (
    FetchResult,
    fetch_url,
    safe_host,
    snapshot_from_fetch,
    snapshot_path,
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    body = b"""
<!doctype html>
<html>
<head><title>Example Longevity Clinic</title><style>.x{}</style></head>
<body>
  <h1>Example Clinic</h1>
  <script>window.secret = "ignore";</script>
  <p>Longevity diagnostics and VO2 max testing.</p>
  <a href="mailto:info@clinic.example">Email</a>
  <a href="tel:+34 600 111 222">Call</a>
</body>
</html>
"""
    snapshot = snapshot_from_fetch(
        FetchResult(
            source_url="https://clinic.example/longevity",
            final_url="https://clinic.example/longevity",
            status_code=200,
            content_type="text/html; charset=utf-8",
            body=body,
        )
    )
    check(snapshot["source_title"] == "Example Longevity Clinic", "title extraction failed")
    check("VO2 max" in snapshot["text_excerpt"], "readable text missing")
    check("info@clinic.example" in snapshot["text_excerpt"], "mailto link should be captured")
    check("+34 600 111 222" in snapshot["text_excerpt"], "tel link should be captured")
    check("window.secret" not in snapshot["text_excerpt"], "script text should be ignored")
    check(len(snapshot["content_sha256"]) == 64, "hash should be sha256")
    check(len(snapshot["text_sha256"]) == 64, "text hash should be sha256")
    check(snapshot["request_profile"] == "vitalarga_bot", "request profile should be captured")
    check(safe_host("https://Clinic.Example/a") == "clinic.example", "host normalization failed")
    path = snapshot_path(snapshot)
    check(str(path).endswith(".json"), "snapshot path should be json")

    boilerplate_body = """
<!doctype html>
<html>
<head><title>Navigation Heavy Clinic</title></head>
<body>
  <div class="site-header">
    <nav class="elementor-nav-menu">
      <a href="/tratamientos-hombre">Tratamientos para hombre</a>
      <a href="/microbiota">Microbiota</a>
      <a href="/tratamientos-hombre">Tratamientos para hombre</a>
      <a href="/microbiota">Microbiota</a>
    </nav>
    <a href="tel:+34 911 111 111">Llamar</a>
  </div>
  <main>
    <h1>Clínica Clara</h1>
    <p>Dirección Calle Serrano 99, 28006 Madrid.</p>
    <p>Equipo médico identificado y tarifas públicas.</p>
  </main>
</body>
</html>
""".encode("utf-8")
    boilerplate_snapshot = snapshot_from_fetch(
        FetchResult(
            source_url="https://clinic.example/",
            final_url="https://clinic.example/",
            status_code=200,
            content_type="text/html; charset=utf-8",
            body=boilerplate_body,
        ),
        excerpt_chars=260,
    )
    boilerplate_excerpt = boilerplate_snapshot["text_excerpt"]
    check("+34 911 111 111" in boilerplate_excerpt, "useful contact links should be kept")
    check("Dirección Calle Serrano" in boilerplate_excerpt, "main clinic content should remain visible")
    check("Tratamientos para hombre" not in boilerplate_excerpt, "navigation text should be suppressed")

    calls = []
    original_open_url = capture_source_snapshot.open_url

    def fake_open_url(url, timeout, headers, request_profile):
        calls.append(request_profile)
        if request_profile == "vitalarga_bot":
            raise urllib.error.HTTPError(url, 403, "Forbidden", {}, None)
        return FetchResult(
            source_url=url,
            final_url=url,
            status_code=200,
            content_type="text/html; charset=utf-8",
            body=b"<html><title>Fallback OK</title></html>",
            request_profile=request_profile,
        )

    try:
        capture_source_snapshot.open_url = fake_open_url
        fallback = fetch_url("https://blocked.example", timeout=5)
    finally:
        capture_source_snapshot.open_url = original_open_url

    check(calls == ["vitalarga_bot", "browser_compatible"], "403 should retry with browser-compatible headers")
    check(fallback.request_profile == "browser_compatible", "fallback profile should be preserved")
    print("OK snapshots: compact source capture")


if __name__ == "__main__":
    main()
