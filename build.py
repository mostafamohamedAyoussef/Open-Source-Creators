"""Vercel build entrypoint.

Assembles a clean ``dist/`` directory: copies the static frontend and dataset,
then generates project pages, per-project JSON, sitemap, and catalog metadata
from ``data/processed_repos.json``. Running this at deploy time keeps the large
generated output (and the raw source scripts) out of git and out of the served
site.
"""

import json
import os
import shutil
from pathlib import Path

from scripts.site_generator import build_site

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"

# Static frontend assets copied verbatim into the deploy output.
STATIC_FILES = ("index.html", "app.js", "styles.css")


def resolve_site_url() -> str | None:
    """Prefer an explicit SITE_URL, else the Vercel-provided production domain."""
    site_url = os.getenv("SITE_URL")
    if not site_url:
        # Vercel injects this (host only, no scheme) for production builds.
        domain = os.getenv("VERCEL_PROJECT_PRODUCTION_URL")
        site_url = f"https://{domain}" if domain else None
    if site_url and not site_url.startswith(("http://", "https://")):
        site_url = f"https://{site_url}"
    return site_url


def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    for name in STATIC_FILES:
        shutil.copy2(ROOT / name, DIST / name)

    (DIST / "data").mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        ROOT / "data" / "processed_repos.json",
        DIST / "data" / "processed_repos.json",
    )

    with open(ROOT / "data" / "processed_repos.json", encoding="utf-8") as f:
        repos = json.load(f)

    site_url = resolve_site_url()
    metadata = build_site(repos, DIST, site_url)
    print(
        f"Built {metadata['total_projects']} project pages into dist/ "
        f"(site_url={site_url or 'relative'})"
    )


if __name__ == "__main__":
    main()
