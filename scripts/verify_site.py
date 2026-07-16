"""Static-output auditor for the generated Open-Source Creators site.

Validates that a generated site directory is internally consistent *before* it
ships. Every check is intentionally cheap: the set of on-disk pages is read once
into a set, and every subsequent check is a set lookup, so the whole audit stays
O(pages + links) over 6,000+ pages.

Usage::

    python scripts/verify_site.py [SITE_ROOT] [--quiet]

Exits 0 when the site is consistent, 1 when any check fails (so CI fails loudly
instead of deploying a broken build). Failures name the offending slug, link, or
file so they are actionable without a second investigation.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree

# Static frontend assets that must survive into the deploy output.
REQUIRED_ASSETS = ("index.html", "app.js", "styles.css", "favicon.svg")

# Related-project links are emitted by site_generator as
# `<a href="../../project/<slug>/">`. The breadcrumb/brand links are plain
# "../../" and are correctly not matched here.
RELATED_LINK_RE = re.compile(r'href="\.\./\.\./project/([^"/]+)/"')

SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"

# Cap how many individual offenders are printed per check; the count is always
# reported in full so a systemic failure does not produce megabytes of log.
MAX_REPORTED = 20


class Report:
    """Collects failures and per-check counters for a single audit run."""

    def __init__(self) -> None:
        self.failures: list[str] = []
        self.counts: dict[str, int] = {}

    def fail(self, message: str) -> None:
        self.failures.append(message)

    def fail_many(self, messages: list[str], summary: str) -> None:
        """Record up to MAX_REPORTED specific failures plus a total."""
        for message in messages[:MAX_REPORTED]:
            self.fail(message)
        if len(messages) > MAX_REPORTED:
            self.fail(
                f"{summary}: {len(messages)} total "
                f"({len(messages) - MAX_REPORTED} more not shown)"
            )

    def count(self, label: str, value: int) -> None:
        self.counts[label] = value

    @property
    def ok(self) -> bool:
        return not self.failures


def discover_pages(root: Path) -> set[str]:
    """Return the slug of every `project/<slug>/index.html` on disk."""
    project_dir = root / "project"
    if not project_dir.is_dir():
        return set()
    return {
        entry.name
        for entry in project_dir.iterdir()
        if entry.is_dir() and (entry / "index.html").is_file()
    }


def check_assets(root: Path, report: Report) -> None:
    missing = [name for name in REQUIRED_ASSETS if not (root / name).is_file()]
    for name in missing:
        report.fail(f"required asset missing from output: {name}")
    report.count("assets checked", len(REQUIRED_ASSETS))


def check_page_parity(root: Path, pages: set[str], report: Report) -> None:
    """catalog-meta.json's total_projects must match the real page count."""
    meta_path = root / "data" / "catalog-meta.json"
    report.count("pages on disk", len(pages))

    if not pages:
        report.fail("no generated project pages found under project/<slug>/index.html")

    if not meta_path.is_file():
        report.fail("data/catalog-meta.json is missing")
        return
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        report.fail(f"data/catalog-meta.json is not valid JSON: {exc}")
        return
    if not isinstance(meta, dict):
        report.fail("data/catalog-meta.json must be a JSON object")
        return

    total = meta.get("total_projects")
    if total is None:
        report.fail("data/catalog-meta.json is missing 'total_projects'")
    elif total != len(pages):
        report.fail(
            f"catalog-meta.json total_projects={total} but {len(pages)} "
            f"project pages exist on disk"
        )
    if not meta.get("generated_at"):
        report.fail("data/catalog-meta.json is missing 'generated_at'")


def check_records(root: Path, pages: set[str], report: Report) -> None:
    """Every page needs its per-project JSON record, and vice versa."""
    records_dir = root / "data" / "projects"
    if not records_dir.is_dir():
        report.fail("data/projects/ directory is missing")
        return
    records = {path.stem for path in records_dir.glob("*.json")}
    report.count("project records", len(records))

    report.fail_many(
        [f"page project/{slug}/ has no data/projects/{slug}.json record" for slug in sorted(pages - records)],
        "pages missing a JSON record",
    )
    report.fail_many(
        [f"record data/projects/{slug}.json has no generated page project/{slug}/" for slug in sorted(records - pages)],
        "records missing a page",
    )


def check_related_links(root: Path, pages: set[str], report: Report) -> None:
    """Every related-project link must resolve to a page that exists on disk.

    Related links come out of the ranking logic rather than the filesystem, so a
    dangling one is exactly the kind of silent regression that ships unnoticed.
    """
    dangling: list[str] = []
    links_checked = 0
    pages_without_related = 0

    for slug in sorted(pages):
        page = root / "project" / slug / "index.html"
        try:
            html = page.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            report.fail(f"could not read project/{slug}/index.html: {exc}")
            continue
        targets = RELATED_LINK_RE.findall(html)
        links_checked += len(targets)
        if not targets:
            pages_without_related += 1
        for target in targets:
            if target not in pages:
                dangling.append(
                    f"project/{slug}/index.html links to ../../project/{target}/ "
                    f"which does not exist"
                )

    report.count("related links checked", links_checked)
    report.fail_many(dangling, "dangling related links")
    if pages_without_related:
        report.count("pages with no related links", pages_without_related)


def check_homepage_index(root: Path, pages: set[str], report: Report) -> None:
    """data/index.json is what the homepage fetches; if it breaks, the site errors."""
    index_path = root / "data" / "index.json"
    if not index_path.is_file():
        report.fail("data/index.json is missing (homepage would show an error state)")
        return
    try:
        entries = json.loads(index_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        report.fail(f"data/index.json is not valid JSON: {exc}")
        return
    if not isinstance(entries, list):
        report.fail(
            f"data/index.json must be a JSON array, got {type(entries).__name__}"
        )
        return

    report.count("index.json entries", len(entries))
    if len(entries) != len(pages):
        report.fail(
            f"data/index.json has {len(entries)} entries but {len(pages)} "
            f"project pages exist on disk"
        )

    problems: list[str] = []
    seen: dict[str, int] = {}
    duplicates: list[str] = []
    for position, entry in enumerate(entries):
        if not isinstance(entry, dict):
            problems.append(f"data/index.json entry #{position} is not an object")
            continue
        path = entry.get("path")
        if not path:
            problems.append(
                f"data/index.json entry #{position} "
                f"({entry.get('name', 'unnamed')!r}) has no 'path'"
            )
            continue
        if path in seen:
            duplicates.append(
                f"data/index.json path {path!r} is duplicated "
                f"(entries #{seen[path]} and #{position}) — slug collision"
            )
        else:
            seen[path] = position
        slug = slug_from_path(path)
        if slug is None:
            problems.append(
                f"data/index.json entry #{position} has malformed path {path!r} "
                f"(expected 'project/<slug>/')"
            )
        elif slug not in pages:
            problems.append(
                f"data/index.json entry #{position} path {path!r} does not resolve "
                f"to a generated page"
            )

    report.fail_many(problems, "broken data/index.json entries")
    report.fail_many(duplicates, "duplicate slugs in data/index.json")


def slug_from_path(path: str) -> str | None:
    """Extract `<slug>` from a flat `project/<slug>/` path, else None."""
    match = re.fullmatch(r"project/([^/]+)/", str(path))
    return match.group(1) if match else None


def check_sitemap(root: Path, pages: set[str], report: Report) -> None:
    """Sitemap must be well-formed and every <loc> must be a real page.

    When no site URL is configured the generator omits absolute locs entirely;
    an empty urlset is therefore valid, not a failure.
    """
    sitemap_path = root / "sitemap.xml"
    if not sitemap_path.is_file():
        report.fail("sitemap.xml is missing")
        return
    try:
        tree = ElementTree.parse(sitemap_path)
    except ElementTree.ParseError as exc:
        report.fail(f"sitemap.xml is not well-formed XML: {exc}")
        return

    root_element = tree.getroot()
    if root_element.tag != f"{SITEMAP_NS}urlset":
        report.fail(
            f"sitemap.xml root element is {root_element.tag!r}, expected a "
            f"sitemaps.org 'urlset'"
        )
        return

    locs = [
        (element.text or "").strip()
        for element in root_element.iter(f"{SITEMAP_NS}loc")
    ]
    report.count("sitemap locs", len(locs))

    if not locs:
        # No site URL configured at build time: relative-only site, nothing to check.
        return

    # With a site URL the generator emits the homepage plus one loc per page.
    if len(locs) != len(pages) + 1:
        report.fail(
            f"sitemap.xml has {len(locs)} <loc> entries but expected "
            f"{len(pages) + 1} ({len(pages)} pages + homepage)"
        )

    problems: list[str] = []
    seen: set[str] = set()
    duplicates: list[str] = []
    homepage_locs = 0
    for loc in locs:
        if not loc:
            problems.append("sitemap.xml contains an empty <loc>")
            continue
        if loc in seen:
            duplicates.append(f"sitemap.xml <loc> {loc} is duplicated")
            continue
        seen.add(loc)
        path = urlsplit(loc).path.lstrip("/")
        if not path:
            homepage_locs += 1
            continue
        slug = slug_from_path(path)
        if slug is None:
            problems.append(f"sitemap.xml <loc> {loc} has an unexpected path {path!r}")
        elif slug not in pages:
            problems.append(
                f"sitemap.xml <loc> {loc} does not resolve to a generated page"
            )

    if homepage_locs == 0:
        problems.append("sitemap.xml does not list the homepage")

    report.fail_many(problems, "broken sitemap entries")
    report.fail_many(duplicates, "duplicate sitemap entries")


def verify_site(root: Path) -> Report:
    """Run every consistency check against a generated site root."""
    root = Path(root)
    report = Report()
    if not root.is_dir():
        report.fail(f"site root does not exist: {root}")
        return report

    pages = discover_pages(root)
    check_assets(root, report)
    check_page_parity(root, pages, report)
    check_records(root, pages, report)
    check_homepage_index(root, pages, report)
    check_related_links(root, pages, report)
    check_sitemap(root, pages, report)
    return report


def render_report(report: Report, root: Path, elapsed: float, quiet: bool) -> str:
    lines = [f"Verifying site output: {root}"]
    if not quiet:
        for label, value in report.counts.items():
            lines.append(f"  {label}: {value}")
    if report.failures:
        lines.append("")
        lines.append(f"FAILED — {len(report.failures)} problem(s):")
        lines.extend(f"  - {failure}" for failure in report.failures)
    else:
        lines.append(f"OK — site output is internally consistent ({elapsed:.2f}s)")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit a generated static site for internal consistency."
    )
    parser.add_argument(
        "root",
        nargs="?",
        default="dist",
        help="generated site root to verify (default: dist)",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="only print failures and the verdict"
    )
    args = parser.parse_args(argv)

    started = time.perf_counter()
    root = Path(args.root)
    report = verify_site(root)
    elapsed = time.perf_counter() - started

    print(render_report(report, root, elapsed, args.quiet))
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
