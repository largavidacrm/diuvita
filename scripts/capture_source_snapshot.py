#!/usr/bin/env python3
"""Capture a compact source snapshot for Vitalarga provenance.

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
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT_DIR = ROOT / "data" / "source_snapshots"
DEFAULT_EXCERPT_CHARS = 1600
USER_AGENT = "VitalargaBot/0.1 (+https://www.vitalarga.com; provenance snapshot)"
BROWSER_COMPAT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.4",
}
BROWSER_COMPAT_HEADERS = {
    "User-Agent": BROWSER_COMPAT_USER_AGENT,
    "Accept": DEFAULT_HEADERS["Accept"],
    "Accept-Language": DEFAULT_HEADERS["Accept-Language"],
    "Upgrade-Insecure-Requests": "1",
}
BOILERPLATE_ATTR_RE = re.compile(
    r"(?:^|[-_\s])(?:"
    r"breadcrumb|breadcrumbs|cookie|cookies|gdpr|legal|main-menu|masthead|"
    r"mega-menu|menu|modal|navbar|navigation|popup|primary-menu|site-header|"
    r"skip-link|social|top-bar|topbar"
    r")(?:$|[-_\s])",
    re.I,
)
BOILERPLATE_TAGS = {"nav"}
CONTACT_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
CONTACT_PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d\s()./-]{7,}\d)(?!\w)")
VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


class ReadableTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title_parts: list[str] = []
        self.meta_description_parts: list[str] = []
        self.text_parts: list[str] = []
        self.contact_parts: list[str] = []
        self._skip_depth = 0
        self._boilerplate_depth = 0
        self._boilerplate_stack: list[bool] = []
        self._in_title = False
        self._contact_href: str | None = None
        self._contact_text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        entered_boilerplate = False
        attr_map = {name.lower(): value or "" for name, value in attrs}
        if tag == "meta":
            meta_key = (attr_map.get("name") or attr_map.get("property") or "").lower()
            if meta_key in {"description", "og:description", "twitter:description"}:
                content = normalize_space(attr_map.get("content") or "")
                if content:
                    self.meta_description_parts.append(content)
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if tag == "a" and not self._skip_depth:
            href = attr_map.get("href") or ""
            if visible_link_value(href):
                self._contact_href = href
                self._contact_text_parts = []
        if tag not in VOID_TAGS and not self._skip_depth and is_boilerplate_tag(tag, attrs):
            self._boilerplate_depth += 1
            entered_boilerplate = True
        if tag not in VOID_TAGS:
            self._boilerplate_stack.append(entered_boilerplate)
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "a" and self._contact_href is not None:
            visible = visible_link_value(self._contact_href, " ".join(self._contact_text_parts))
            if visible:
                self.contact_parts.append(visible)
            self._contact_href = None
            self._contact_text_parts = []
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if self._boilerplate_stack:
            exited_boilerplate = self._boilerplate_stack.pop()
        else:
            exited_boilerplate = tag in BOILERPLATE_TAGS
        if exited_boilerplate and self._boilerplate_depth:
            self._boilerplate_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        clean = normalize_space(data)
        if not clean:
            return
        if self._contact_href is not None and not self._skip_depth:
            self._contact_text_parts.append(clean)
        if self._in_title:
            self.title_parts.append(clean)
        elif not self._skip_depth and not self._boilerplate_depth:
            self.text_parts.append(clean)

    @property
    def title(self) -> str:
        return normalize_space(" ".join(self.title_parts))

    @property
    def readable_text(self) -> str:
        parts = compact_readable_parts([*self.contact_parts, *self.meta_description_parts, *self.text_parts])
        return normalize_space(" ".join(parts))


@dataclass(frozen=True)
class FetchResult:
    source_url: str
    final_url: str
    status_code: int | None
    content_type: str
    body: bytes
    request_profile: str = "vitalarga_bot"


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def comparable_text(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    return normalize_space(folded).lower()


def is_boilerplate_tag(tag: str, attrs: list[tuple[str, str | None]]) -> bool:
    if tag in BOILERPLATE_TAGS:
        return True
    attr_values = " ".join(value or "" for name, value in attrs if name.lower() in {"class", "id", "role"})
    return bool(attr_values and BOILERPLATE_ATTR_RE.search(attr_values))


def compact_readable_parts(parts: list[str]) -> list[str]:
    seen: set[str] = set()
    compacted: list[str] = []
    previous_key = ""
    for part in parts:
        clean = normalize_space(part)
        if not clean:
            continue
        key = comparable_text(clean)
        if key == previous_key:
            continue
        if key in seen and len(clean) <= 180:
            continue
        seen.add(key)
        previous_key = key
        compacted.append(clean)
    return compacted


def visible_link_value(href: str, label: str = "") -> str:
    visible_label = normalize_space(label)
    label_email = CONTACT_EMAIL_RE.search(visible_label)
    if label_email:
        return label_email.group(0).strip()
    label_phone = CONTACT_PHONE_RE.search(visible_label)
    if label_phone:
        return label_phone.group(0).strip(".,;:")
    if "instagram.com/" in visible_label.lower():
        return visible_label

    clean = normalize_space(unquote(href))
    lower = clean.lower()
    if lower.startswith("mailto:"):
        return clean[7:].split("?", 1)[0].strip()
    if lower.startswith("tel:"):
        return clean[4:].split("?", 1)[0].strip()
    if "instagram.com/" in lower:
        return clean
    return ""


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


def open_url(url: str, timeout: int, headers: dict[str, str], request_profile: str) -> FetchResult:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return FetchResult(
            source_url=url,
            final_url=response.geturl(),
            status_code=getattr(response, "status", None),
            content_type=response.headers.get("content-type", ""),
            body=response.read(),
            request_profile=request_profile,
        )


def fetch_url(url: str, timeout: int = 20) -> FetchResult:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("source URL must start with http:// or https://")
    try:
        return open_url(url, timeout, DEFAULT_HEADERS, "vitalarga_bot")
    except urllib.error.HTTPError as error:
        if error.code not in {403, 406}:
            raise
        return open_url(url, timeout, BROWSER_COMPAT_HEADERS, "browser_compatible")


def snapshot_from_fetch(result: FetchResult, excerpt_chars: int = DEFAULT_EXCERPT_CHARS) -> dict[str, Any]:
    html_text = decode_body(result.body, result.content_type)
    title, readable_text = parse_html(html_text)
    digest = hashlib.sha256(result.body).hexdigest()
    text_digest = hashlib.sha256(readable_text.encode("utf-8")).hexdigest() if readable_text else None
    return {
        "source_url": result.source_url,
        "final_url": result.final_url,
        "source_title": title or None,
        "source_type": "website",
        "retrieved_at": now_iso(),
        "http_status": result.status_code,
        "content_type": result.content_type or None,
        "request_profile": result.request_profile,
        "content_sha256": digest,
        "text_sha256": text_digest,
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
