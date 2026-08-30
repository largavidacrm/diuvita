#!/usr/bin/env python3
"""Checks that the admin dashboard shows source snapshot retention status."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    index = (ROOT / "admin" / "index.html").read_text(encoding="utf-8")

    for marker in [
        "SNAPSHOT_RETENTION_DAYS",
        "SNAPSHOT_KEEP_LATEST",
        "function emptySourceSnapshotRetention",
        "function sourceSnapshotRetentionStatus",
        "monitoring.snapshotRetention = sourceSnapshotRetentionStatus(snapshots);",
        "Retención capturas",
        "Inventario capturas",
        "Sin limpieza",
        "candidatas",
        "antiguas ·",
    ]:
        check(marker in index, f"missing admin snapshot retention marker: {marker}")

    check(
        '.from("source_snapshots")' in index and '.select("source_record_id, retrieved_at")' in index,
        "dashboard should read compact source snapshots for retention status",
    )
    print("OK admin snapshot retention: status visible")


if __name__ == "__main__":
    main()
