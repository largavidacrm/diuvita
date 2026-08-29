# -*- coding: utf-8 -*-
"""Print one SQL bundle with the foundation migration and current clinic seed."""
from pathlib import Path

import export_supabase_seed

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase" / "migrations" / "0001_agent_foundation.sql"


def main():
    print("-- Diuvita Supabase bootstrap")
    print("-- 1) Foundation schema")
    print(MIGRATION.read_text(encoding="utf-8").strip())
    print()
    print("-- 2) Current clinic seed")
    export_supabase_seed.main()


if __name__ == "__main__":
    main()
