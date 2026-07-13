import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from html import escape as html_escape
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

# Self-contained stylesheet so each project page renders correctly without an
# extra network request or a relative path back to the site root.
PAGE_STYLE = """
  :root { color-scheme: light dark; }
  * { box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    line-height: 1.6; margin: 0; padding: 2rem 1rem;
    background: #0f172a; color: #e2e8f0;
  }
  main { max-width: 760px; margin: 0 auto; }
  nav[aria-label="Breadcrumb"] { margin-bottom: 1.5rem; font-size: 0.9rem; }
  a { color: #60a5fa; }
  h1 { font-size: 2rem; margin: 0 0 0.5rem; color: #f8fafc; }
  h2 { font-size: 1.15rem; margin: 2rem 0 0.75rem; color: #f8fafc;
       border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 0.4rem; }
  dl { display: grid; grid-template-columns: max-content 1fr; gap: 0.4rem 1.5rem; margin: 0; }
  dt { color: #94a3b8; } dd { margin: 0; }
  ul { padding-left: 1.2rem; } li { margin: 0.2rem 0; }
  section ul.tags, section ul.categories, section ul.alternatives {
    list-style: none; padding: 0; display: flex; flex-wrap: wrap; gap: 0.5rem;
  }
  section ul.tags li, section ul.categories li, section ul.alternatives li {
    background: rgba(59,130,246,0.15); color: #93c5fd;
    padding: 0.25rem 0.6rem; border-radius: 6px; font-size: 0.85rem;
  }
"""


def make_project_slug(repo: dict) -> str:
    raw = str(repo.get("full_name") or repo.get("name") or "project").lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", raw).strip("-") or "project"
    return f"{normalized}-{repo['id']}"


def build_project_record(repo: dict, generated_at: str) -> dict:
    record = deepcopy(repo)
    # Normalize nullable list fields so downstream code can assume consistent types.
    record["categories"] = record.get("categories") or []
    record["tags"] = record.get("tags") or []
    record["commercial_alternatives"] = record.get("commercial_alternatives") or []
    slug = make_project_slug(repo)
    record["project"] = {
        "id": repo["id"],
        "slug": slug,
        "path": f"project/{slug}/",
        "generated_at": generated_at,
    }
    return record


def rank_related_projects(
    project: dict, candidates: list[dict], limit: int = 6
) -> list[dict]:
    project_categories = set(project.get("categories") or [])
    project_tags = set(project.get("tags") or [])
    project_alternatives = set(project.get("commercial_alternatives") or [])
    project_language = project.get("language")

    def relevance(candidate: dict) -> int:
        shared_categories = len(project_categories & set(candidate.get("categories") or []))
        shared_tags = len(project_tags & set(candidate.get("tags") or []))
        shared_alternatives = len(
            project_alternatives & set(candidate.get("commercial_alternatives") or [])
        )
        same_language = bool(project_language) and candidate.get("language") == project_language
        return (
            3 * shared_categories
            + 2 * shared_tags
            + 2 * shared_alternatives
            + int(same_language)
        )

    related = [
        candidate for candidate in candidates if candidate.get("id") != project.get("id")
    ]
    related.sort(
        key=lambda candidate: (
            relevance(candidate),
            candidate.get("score", 0),
            candidate.get("stargazers_count", 0),
        ),
        reverse=True,
    )
    return related[:limit]


def build_site(repos: list[dict], root_dir: Path, site_url: str | None = None) -> dict:
    """Write static project pages and their supporting catalog artifacts."""
    root_dir = Path(root_dir)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )
    public_url = site_url.rstrip("/") if site_url else None
    projects_dir = root_dir / "data" / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)

    records = []
    for repo in repos:
        record = build_project_record(repo, generated_at)
        related = rank_related_projects(repo, repos)
        record["related_projects"] = [
            {
                "id": candidate["id"],
                "name": candidate.get("name") or candidate.get("full_name") or "Project",
                "slug": make_project_slug(candidate),
                "path": f"project/{make_project_slug(candidate)}/",
            }
            for candidate in related
        ]
        records.append(record)

        slug = record["project"]["slug"]
        (projects_dir / f"{slug}.json").write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        page_dir = root_dir / "project" / slug
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "index.html").write_text(
            _render_project_page(record, public_url), encoding="utf-8"
        )

    metadata = {"generated_at": generated_at, "total_projects": len(records)}
    (root_dir / "data" / "catalog-meta.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (root_dir / "sitemap.xml").write_text(
        _render_sitemap(records, public_url), encoding="utf-8"
    )
    return metadata


def _render_project_page(record: dict, site_url: str | None) -> str:
    project = record["project"]
    name = record.get("name") or record.get("full_name") or "Project"
    description = record.get("description") or "No description provided."
    canonical = (
        f'<link rel="canonical" href="{html_escape(site_url + "/" + project["path"])}">'
        if site_url
        else ""
    )
    source_url = record.get("html_url")
    source_link = (
        f'<a href="{html_escape(str(source_url), quote=True)}">View on GitHub</a>'
        if source_url
        else ""
    )
    facts = (
        ("Stars", record.get("stargazers_count")),
        ("Forks", record.get("forks_count")),
        ("Language", record.get("language")),
        ("License", record.get("license")),
        ("Created", record.get("created_at")),
        ("Last updated", record.get("updated_at")),
        ("Repository", source_url),
    )
    fact_markup = "".join(
        f"<dt>{label}</dt><dd>{html_escape(str(value)) if value is not None else '—'}</dd>"
        for label, value in facts
    )
    tags = _render_list(record.get("tags") or [], "tags")
    alternatives = _render_list(record.get("commercial_alternatives") or [], "alternatives")
    categories = _render_list(record.get("categories") or [], "categories")
    related = "".join(
        f'<li><a href="../../{html_escape(item["path"], quote=True)}">'
        f'{html_escape(str(item["name"]))}</a></li>'
        for item in record["related_projects"]
    ) or "<li>None yet.</li>"
    escaped_name = html_escape(str(name))
    escaped_description = html_escape(str(description))
    json_ld = _render_json_ld(record, site_url)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escaped_name} | Open-Source Content Creation Directory</title>
  <meta name="description" content="{html_escape(str(description), quote=True)}">
  <meta property="og:title" content="{html_escape(str(name), quote=True)}">
  <meta property="og:description" content="{html_escape(str(description), quote=True)}">
  <meta property="og:type" content="website">
  <meta name="twitter:card" content="summary">
  {canonical}
  <style>{PAGE_STYLE}</style>
  {json_ld}
</head>
<body>
  <main>
    <nav aria-label="Breadcrumb"><a href="../../">Directory</a></nav>
    <article>
      <h1>{escaped_name}</h1>
      <p>{escaped_description}</p>
      <p>{source_link}</p>
      <section><h2>Facts</h2><dl>{fact_markup}</dl></section>
      <section><h2>Categories</h2>{categories}</section>
      <section><h2>Tags</h2>{tags}</section>
      <section><h2>Commercial alternatives</h2>{alternatives}</section>
      <section><h2>Related projects</h2><ul>{related}</ul></section>
      <p>Last data refresh: {html_escape(project["generated_at"])}</p>
    </article>
  </main>
</body>
</html>
"""


def _render_json_ld(record: dict, site_url: str | None) -> str:
    """Emit SoftwareApplication structured data for richer search results."""
    data = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": record.get("name") or record.get("full_name") or "Project",
        "applicationCategory": "MultimediaApplication",
    }
    if record.get("description"):
        data["description"] = record["description"]
    if record.get("html_url"):
        data["codeRepository"] = record["html_url"]
    if record.get("license"):
        data["license"] = record["license"]
    if record.get("language"):
        data["programmingLanguage"] = record["language"]
    if site_url:
        data["url"] = site_url + "/" + record["project"]["path"]
    # json.dumps escapes quotes; wrap in a script tag. "</" is neutralized so the
    # payload cannot break out of the script element.
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/ld+json">{payload}</script>'


def _render_list(values: list, css_class: str) -> str:
    if not values:
        return "<p>—</p>"
    return '<ul class="{}">{}</ul>'.format(
        css_class,
        "".join(f"<li>{html_escape(str(value))}</li>" for value in values),
    )


def _render_sitemap(records: list[dict], site_url: str | None) -> str:
    urls = ["" ] if site_url else []
    if site_url:
        urls.extend(record["project"]["path"] for record in records)
    entries = "".join(
        f"  <url><loc>{xml_escape(site_url + '/' + path)}</loc></url>\n" for path in urls
    )
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + entries + "</urlset>\n"
