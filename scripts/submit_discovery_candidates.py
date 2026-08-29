#!/usr/bin/env python3
"""Submit DISCOVER_CLINIC shadow candidates into Supabase review_queue.

This is a trusted local operator tool: it uses the database password from .env
and never publishes a clinic. Candidates become review cards first.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(ROOT, ".env")
PROJECT_REF = "twxhcmvzbpnrneywdece"


def load_env_file():
    values = {}
    if not os.path.exists(ENV_FILE):
        return values
    with open(ENV_FILE, encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip("\"'")
    return values


def env_or_file(key, local_env, default=""):
    return os.environ.get(key) or local_env.get(key) or default


def find_psql():
    configured = os.environ.get("PSQL")
    if configured:
        return configured
    found = shutil.which("psql")
    if found:
        return found
    homebrew = "/opt/homebrew/opt/libpq/bin/psql"
    if os.path.exists(homebrew):
        return homebrew
    raise SystemExit("psql was not found.")


def sql_literal(value):
    if value is None:
        return "null"
    return "'" + str(value).replace("'", "''") + "'"


def run_psql(sql, local_env):
    password = env_or_file("SUPABASE_DB_PASSWORD", local_env)
    if not password:
        raise SystemExit("Set SUPABASE_DB_PASSWORD in .env first.")

    env = os.environ.copy()
    env["PGPASSWORD"] = password
    env["PGSSLMODE"] = "require"

    command = [
        find_psql(),
        "-h",
        env_or_file("SUPABASE_DB_HOST", local_env, f"db.{PROJECT_REF}.supabase.co"),
        "-p",
        env_or_file("SUPABASE_DB_PORT", local_env, "5432"),
        "-d",
        env_or_file("SUPABASE_DB_NAME", local_env, "postgres"),
        "-U",
        env_or_file("SUPABASE_DB_USER", local_env, "postgres"),
        "-v",
        "ON_ERROR_STOP=1",
        "-At",
    ]
    result = subprocess.run(
        command,
        input=sql,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)
    return result.stdout.strip()


def get_default_admin_email(local_env):
    configured = env_or_file("SUPABASE_ADMIN_EMAIL", local_env)
    if configured:
        return configured
    sql = """
select lower(email)
from public.admin_users
where active = true
order by case when role = 'owner' then 0 else 1 end, created_at asc
limit 1;
"""
    email = run_psql(sql, local_env).strip()
    if not email:
        raise SystemExit("No active admin email found.")
    return email


def load_candidates(path):
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, dict) and isinstance(data.get("candidates"), list):
        data = data["candidates"]
    if not isinstance(data, list):
        raise SystemExit("Candidates file must be a JSON list or an object with a candidates list.")
    clean = []
    for item in data:
        if isinstance(item, dict):
            clean.append(item)
    if not clean:
        raise SystemExit("Candidates file does not contain any candidate objects.")
    return clean


def create_job(query, country, local_env):
    payload = json.dumps(
        {
            "query": query,
            "country": country,
            "mode": "shadow",
        },
        ensure_ascii=False,
    )
    sql = f"""
insert into public.agent_jobs (
  job_type,
  status,
  priority,
  input,
  model_tier,
  requires_human
)
values (
  'DISCOVER_CLINIC',
  'queued',
  100,
  {sql_literal(payload)}::jsonb,
  'manual',
  false
)
returning id;
"""
    return run_psql(sql, local_env).splitlines()[-1].strip()


def pick_next_job(admin_email, worker, local_env):
    sql = f"""
with claims as (
  select set_config(
    'request.jwt.claims',
    jsonb_build_object('email', {sql_literal(admin_email)})::text,
    true
  )
)
select public.admin_pick_agent_job({sql_literal(worker)}, 'DISCOVER_CLINIC')
from claims;
"""
    output = run_psql(sql, local_env).strip()
    if not output or output == "null":
        return None
    picked = json.loads(output)
    return picked["id"]


def complete_job(job_id, candidates, admin_email, note, confidence, cost_cents, local_env):
    candidate_json = json.dumps(candidates, ensure_ascii=False)
    confidence_sql = "null" if confidence is None else str(confidence)
    sql = f"""
with claims as (
  select set_config(
    'request.jwt.claims',
    jsonb_build_object('email', {sql_literal(admin_email)})::text,
    true
  )
)
select public.admin_complete_discovery_job(
  {sql_literal(job_id)}::uuid,
  {sql_literal(candidate_json)}::jsonb,
  {sql_literal(note)}::text,
  {confidence_sql}::numeric,
  {int(cost_cents)}::integer
)
from claims;
"""
    output = run_psql(sql, local_env).splitlines()[-1]
    return json.loads(output)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", required=True, help="JSON list of candidate clinics.")
    parser.add_argument("--job-id", help="Existing DISCOVER_CLINIC job id.")
    parser.add_argument("--pick-next", action="store_true", help="Use the next queued discovery job.")
    parser.add_argument("--create-job", help="Create a new shadow discovery job with this query.")
    parser.add_argument("--country", default="España")
    parser.add_argument("--admin-email", help="Admin email used for audit attribution.")
    parser.add_argument("--worker", default="local-shadow-worker")
    parser.add_argument("--note", default="")
    parser.add_argument("--confidence", type=float)
    parser.add_argument("--cost-cents", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    local_env = load_env_file()
    candidates = load_candidates(args.candidates)

    if args.confidence is not None and not 0 <= args.confidence <= 1:
        raise SystemExit("--confidence must be between 0 and 1.")
    if args.cost_cents < 0:
        raise SystemExit("--cost-cents cannot be negative.")

    if args.dry_run:
        print(f"OK dry run: {len(candidates)} candidates loaded.")
        for candidate in candidates[:10]:
            print("- " + str(candidate.get("name") or candidate.get("website") or candidate))
        return

    admin_email = args.admin_email or get_default_admin_email(local_env)
    job_id = args.job_id
    if args.create_job:
        job_id = create_job(args.create_job, args.country, local_env)
    elif args.pick_next:
        job_id = pick_next_job(admin_email, args.worker, local_env)

    if not job_id:
        raise SystemExit("Provide --job-id, --pick-next, or --create-job.")

    result = complete_job(
        job_id=job_id,
        candidates=candidates,
        admin_email=admin_email,
        note=args.note,
        confidence=args.confidence,
        cost_cents=args.cost_cents,
        local_env=local_env,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
