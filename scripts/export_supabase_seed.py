# -*- coding: utf-8 -*-
"""Print SQL that imports current JSON clinics into the Supabase foundation schema."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLINICS_FILE = ROOT / "data" / "clinics.json"

STATUS_MAP = {
    "publicada": "published",
    "preliminar": "preliminary",
}


def sql_string(value):
    if value is None:
        return "null"
    return "'" + str(value).replace("'", "''") + "'"


def sql_json(value):
    return sql_string(json.dumps(value, ensure_ascii=False, sort_keys=True)) + "::jsonb"


def main():
    clinics = json.loads(CLINICS_FILE.read_text(encoding="utf-8"))
    print("-- Generated from data/clinics.json. Review before running in Supabase.")
    print("begin;")
    for clinic in clinics:
        status = STATUS_MAP.get(clinic.get("status"), "draft")
        print(
            "insert into public.clinics "
            "(slug, canonical_name, display_name, website, country, city, address, status, summary, current_data, profile_confidence, verification_status) "
            "values "
            f"({sql_string(clinic.get('slug'))}, "
            f"{sql_string(clinic.get('name'))}, "
            f"{sql_string(clinic.get('name'))}, "
            f"{sql_string(clinic.get('web'))}, "
            f"{sql_string(clinic.get('country'))}, "
            f"{sql_string(clinic.get('city'))}, "
            f"{sql_string(clinic.get('address'))}, "
            f"{sql_string(status)}, "
            f"{sql_string(clinic.get('summary'))}, "
            f"{sql_json(clinic)}, "
            "0.8000, "
            "'human_curated') "
            "on conflict (slug) do update set "
            "canonical_name = excluded.canonical_name, "
            "display_name = excluded.display_name, "
            "website = excluded.website, "
            "country = excluded.country, "
            "city = excluded.city, "
            "address = excluded.address, "
            "status = excluded.status, "
            "summary = excluded.summary, "
            "current_data = excluded.current_data, "
            "updated_at = now();"
        )
    print("commit;")


if __name__ == "__main__":
    main()
