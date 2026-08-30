#!/usr/bin/env python3
"""Checks for Netlify production-build skipping rules."""

import netlify_ignore_build as ignore


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def skips(paths):
    should_skip, _reasons = ignore.should_skip_build(paths)
    return should_skip


def main():
    check(skips(["README.md", "docs/NETLIFY_DEPLOY_CONTROL.md"]), "docs should skip")
    check(skips(["scripts/global_plan_status.py"]), "internal scripts should skip")
    check(skips(["supabase/migrations/0018_batch_public_site_rebuilds.sql"]), "migrations should skip")
    check(skips(["pendientes/README.md"]), "pending private files should skip")
    check(not skips(["admin/index.html"]), "admin changes should build")
    check(not skips(["admin/admin.css"]), "admin styles should build")
    check(not skips(["data/clinics.json"]), "clinic data should build")
    check(not skips(["data/posts/que-es-una-clinica-de-longevidad.md"]), "posts should build")
    check(not skips(["assets/logos/thumb/monarka-clinic.png"]), "assets should build")
    check(not skips(["build.py"]), "build generator should build")
    check(not skips(["netlify.toml"]), "Netlify config should build")
    check(not skips(["new-public-file.html"]), "unknown files should build safely")
    print("OK netlify ignore build: deploy guard is conservative")


if __name__ == "__main__":
    main()
