#!/usr/bin/env python3
"""Checks that the admin dashboard shows source monitoring freshness."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    index = (ROOT / "admin" / "index.html").read_text(encoding="utf-8")

    for marker in [
        "DEFAULT_MONITOR_CADENCE_DAYS",
        "function monitorCadenceDays",
        "function sourceMonitoringStatus",
        "function loadSourceMonitoring",
        '.from("source_records")',
        '.from("source_snapshots")',
        "Vigilancia fuentes",
        "Todo reciente",
        "pendientes",
        "Próxima revisión fuentes",
        "Fuente más vencida",
        "var sourceMonitoring = await loadSourceMonitoring();",
    ]:
        check(marker in index, f"missing admin source monitoring marker: {marker}")

    check(
        "renderSystemStatus(summary, jobRows.data || [], eventRows.data || [], claimQuality, sourceMonitoring);"
        in index,
        "dashboard should render source monitoring status",
    )
    print("OK admin source monitoring: freshness visible")


if __name__ == "__main__":
    main()
