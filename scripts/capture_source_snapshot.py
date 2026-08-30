#!/usr/bin/env python3
"""Capture a compact source snapshot for Diuvita provenance.

By default this stores metadata, a content hash and a short text excerpt rather
than the full page. That is enough for audit trails without turning the repo into
a copy of external websites.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT_DIR = ROOT / "data" / "source_snapshots"
DEFAULT_EXCERPT_CHARS = 1600
USER_AGENT = "DiuvitaBot/0.1 (+https://www.diuvita.com; provenance snapshot)"


class ReadableTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        clean = normalize_space(data)
        if not clean:
            return
        if self._in_title:
            self.title_parts.append(clean)
        elif not self._skip_depth:
            self.text_parts.append(clean)

    @property
    def title(self) -> str:
        return normalize_space(" ".join(self.title_parts))

    @property
    def readable_text(self) -> str:
        return normalize_space(" ".join(self.text_parts))


@dataclass(frozen=True)
class FetchResult:
    source_url: str
    final_url: str
    status_code: int | None
    content_type: str
    body: bytes


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def decode_body(body: bytes, content_type: str = "") -> str:
    charset_match = re.search(r"charset=([^;\s]+)", content_type or "", flags=re.I)
    encodings = []
    if charset_match:
        encodings.append(charset_match.group(1).strip("\"'"))
    encodings.extend(["utf-8", "latin-1"])
    for encoding in encodings:
        try:
            return body.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return body.decode("utf-8", errors="replace")


def parse_html(html_text: str) -> tuple[str, str]:
    parser = ReadableTextParser()
    parser.feed(html_text)
    return parser.title, parser.readable_text


def fetch_url(url: str, timeout: int = 20) -> FetchResult:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("source URL must start with http:// or https://")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return FetchResult(
            source_url=url,
            final_url=response.geturl(),
            status_code=getattr(response, "status", None),
            content_type=response.headers.get("content-type", ""),
            body=response.read(),
        )


def snapshot_from_fetch(result: FetchResult, excerpt_chars: int = DEFAULT_EXCERPT_CHARS) -> dict[str, Any]:
    html_text = decode_body(result.body, result.content_type)
    title, readable_text = parse_html(html_text)
    digest = hashlib.sha256(result.body).hexdigest()
    return {
        "source_url": result.source_url,
        "final_url": result.final_url,
        "source_title": title or None,
        "source_type": "website",
        "retrieved_at": now_iso(),
        "http_status": result.status_code,
        "content_type": result.content_type or None,
        "content_sha256": digest,
        "content_length": len(result.body),
        "text_excerpt": readable_text[:excerpt_chars] or None,
    }


def safe_host(url: str) -> str:
    host = urlparse(url).netloc.lower() or "unknown-host"
    return re.sub(r"[^a-z0-9.-]+", "-", host).strip("-") or "unknown-host"


def snapshot_path(snapshot: dict[str, Any], base_dir: Path = DEFAULT_SNAPSHOT_DIR) -> Path:
    retrieved = str(snapshot.get("retrieved_at") or now_iso())
    year = retrieved[:4]
    month = retrieved[5:7]
    digest = str(snapshot.get("content_sha256") or "nohash")[:16]
    return base_dir / year / month / safe_host(str(snapshot.get("final_url") or snapshot.get("source_url"))) / f"{digest}.json"


def write_snapshot(snapshot: dict[str, Any], base_dir: Path = DEFAULT_SNAPSHOT_DIR) -> Path:
    path = snapshot_path(snapshot, base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_from_html_file(path: Path, source_url: str) -> FetchResult:
    body = path.read_bytes()
    return FetchResult(
        source_url=source_url,
        final_url=source_url,
        status_code=None,
        content_type="text/html; charset=utf-8",
        body=body,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="Public source URL.")
    parser.add_argument("--html-file", type=Path, help="Use a local HTML file instead of fetching the URL.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_SNAPSHOT_DIR)
    parser.add_argument("--excerpt-chars", type=int, default=DEFAULT_EXCERPT_CHARS)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.excerpt_chars < 200 or args.excerpt_chars > 5000:
        raise SystemExit("--excerpt-chars must be between 200 and 5000")
    if args.html_file:
        result = load_from_html_file(args.html_file, args.url)
    else:
        result = fetch_url(args.url)
    snapshot = snapshot_from_fetch(result, excerpt_chars=args.excerpt_chars)
    if args.dry_run:
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))
        return 0
    path = write_snapshot(snapshot, args.output_dir)
    print(os.path.relpath(path, ROOT))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
