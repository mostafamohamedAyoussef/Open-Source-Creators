# Project Pages & Editorial Directory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship an elegant static creator-tools directory with a canonical page for every project, stable project records, explainable recommendations, and a premium responsive frontend.

**Architecture:** The processor normalizes GitHub data and calls a new pure-Python static-site generator. It writes per-project JSON, rendered project pages, catalog metadata, and a sitemap. The homepage remains a small client-side catalog that links to self-contained project pages.

**Tech Stack:** Python 3.11 standard library, `unittest`, vanilla HTML/CSS/JavaScript, GitHub Pages, GitHub Actions.

## Global Constraints

- Keep deployment fully static and GitHub Pages compatible.
- Do not add a client framework, database, Node build step, or runtime dependency.
- Stable identity derives from GitHub numeric repository ID.
- Render only collected facts; do not invent installation or project metadata.
- Use warm paper, near-ink, cobalt accents, restrained amber status, a display serif plus workhorse sans, and no gradients or glassmorphism.
- Every behavior change starts with a failing automated test.
- Generated output is reproducible from `data/processed_repos.json`.

---

## Roadmap: Original Vision as Milestones

### Milestone 1 — Canonical catalog (this plan)

Project pages, static SEO, normalized project artifacts, deterministic related projects, premium discovery UI, accessibility, and safe rendering. Covers original items 1, an explainable first version of 3, parts of 4, 8 and 9, plus the architecture recommendation.

### Milestone 2 — Historical intelligence

Daily snapshots, growth deltas, changelog/release ingestion, timelines, transparent community-health factors, and a defined trending calculation. Covers 2, 13, 16, 17, and 19.

### Milestone 3 — Decision-oriented discovery

Commercial-alternative landing pages, sourced comparison pages, advanced filters, installation-difficulty rubric, curated collections, and relationship tuning. Covers 5, 6, 10, 14, and 15.

### Milestone 4 — Semantic curation and workflows

Reviewed AI summaries, embedding search, licensed visual sourcing, stack-builder recommendations, richer ingestion, and data-quality pipeline. Covers 7, 11, 12, 22, and 23.

### Milestone 5 — Platform layer

Bookmarks, explainable personalization, public versioned API, MCP server, rate limits, and developer documentation. Covers 18, 20, and 21.

Each milestone ends with data-quality, accessibility, responsive, static-output, and deployment audits before the next begins.

## Task 1: Test and add project-record helpers

**Files:**
- Create: `scripts/site_generator.py`
- Create: `tests/test_site_generator.py`

**Interfaces:**
- Produces: `make_project_slug(repo: dict) -> str`, `build_project_record(repo: dict, generated_at: str) -> dict`, and `rank_related_projects(project: dict, candidates: list[dict], limit: int = 6) -> list[dict]`.

- [ ] **Step 1: Write failing slug and record tests**

```python
def test_slug_is_stable_and_normalized(self):
    self.assertEqual(make_project_slug({"id": 42, "full_name": "Acme/Creative Tool!"}), "acme-creative-tool-42")

def test_record_does_not_mutate_source(self):
    source = {"id": 42, "full_name": "Acme/Creative Tool!"}
    record = build_project_record(source, "2026-07-12T00:00:00Z")
    self.assertEqual(record["project"]["path"], "project/acme-creative-tool-42/")
    self.assertNotIn("project", source)
```

- [ ] **Step 2: Verify red**

Run: `python -m unittest tests.test_site_generator -v`

Expected: import failure for absent `scripts.site_generator`.

- [ ] **Step 3: Implement the smallest helpers**

```python
def make_project_slug(repo):
    raw = str(repo.get("full_name") or repo.get("name") or "project").lower()
    return f"{re.sub(r'[^a-z0-9]+', '-', raw).strip('-') or 'project'}-{repo['id']}"

def build_project_record(repo, generated_at):
    record = deepcopy(repo)
    slug = make_project_slug(repo)
    record["project"] = {"id": repo["id"], "slug": slug, "path": f"project/{slug}/", "generated_at": generated_at}
    return record
```

- [ ] **Step 4: Verify green, then add a failing ranking test**

Run: `python -m unittest tests.test_site_generator -v`

Test that a shared category/tag match ranks ahead of a higher-scored candidate with only a matching language, and that the current project is excluded.

- [ ] **Step 5: Implement explainable ranking and verify**

Score candidates as `3 * shared_categories + 2 * shared_tags + 2 * shared_commercial_alternatives + 1 * same_language`; tie-break by score then stars. Return at most six candidates. Run `python -m unittest tests.test_site_generator -v` and expect green.

- [ ] **Step 6: Commit**

Run: `git add scripts/site_generator.py tests/test_site_generator.py && git commit -m "feat: add tested project record generation"`

## Task 2: Generate static project pages, data artifacts, and sitemap

**Files:**
- Modify: `scripts/site_generator.py`
- Modify: `tests/test_site_generator.py`

**Interfaces:**
- Produces: `build_site(repos: list[dict], root_dir: Path, site_url: str | None = None) -> dict`, `data/projects/<slug>.json`, `project/<slug>/index.html`, `data/catalog-meta.json`, and `sitemap.xml`.

- [ ] **Step 1: Write the failing static-output test**

```python
def test_build_site_writes_escaped_page_json_and_sitemap(self):
    repos = [{"id": 42, "full_name": "Acme/Creative Tool", "name": "Creative <Tool>", "description": "Use & share", "categories": ["Audio"], "tags": ["tts"], "commercial_alternatives": [], "language": "Python", "license": "MIT", "stargazers_count": 1, "forks_count": 2, "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-07-01T00:00:00Z", "html_url": "https://github.com/acme/tool", "score": 8}]
    build_site(repos, self.root, "https://example.github.io/catalog")
    self.assertIn("Creative &lt;Tool&gt;", (self.root / "project/acme-creative-tool-42/index.html").read_text())
    self.assertTrue((self.root / "data/projects/acme-creative-tool-42.json").exists())
```

- [ ] **Step 2: Verify red**

Run: `python -m unittest tests.test_site_generator -v`

Expected: missing output files.

- [ ] **Step 3: Implement output generation**

Use `html.escape` on every source-derived HTML string and `xml.sax.saxutils.escape` for sitemap values. Render one `h1`, source/GitHub link, facts, tags, alternatives, related-project links, generated timestamp, and a canonical link only when `site_url` is supplied. Write UTF-8, indented JSON and create parent directories through `Path.mkdir(parents=True, exist_ok=True)`.

- [ ] **Step 4: Verify green**

Run: `python -m unittest tests.test_site_generator -v && python -m unittest discover -v`

Expected: all tests pass.

- [ ] **Step 5: Commit**

Run: `git add scripts/site_generator.py tests/test_site_generator.py && git commit -m "feat: generate static project pages and sitemap"`

## Task 3: Integrate generation with ingestion and deployment

**Files:**
- Modify: `scripts/collector.py`
- Modify: `scripts/processor.py`
- Modify: `.github/workflows/update.yml`
- Modify: `README.md`
- Create: `tests/test_processor.py`

**Interfaces:**
- Consumes: GitHub item `id` and optional `SITE_URL`.
- Produces: generated artifacts whenever `processor.py` runs.

- [ ] **Step 1: Write a failing processor integration test**

Write a one-record raw fixture (`id: 42`) in a temporary project root, call `process_repos(root_dir=tmp_path)`, and assert both preserved `id` in processed data and generated `project/acme-creative-tool-42/index.html`.

- [ ] **Step 2: Verify red**

Run: `python -m unittest tests.test_processor -v`

Expected: failing because collector records lack `id`, `process_repos` has no root parameter, or no project page is generated.

- [ ] **Step 3: Implement narrow pipeline changes**

Store `"id": repo_id` in `collector.py`. Let `process_repos` accept an optional root directory, retain its default root, and call `build_site(processed, root_dir, os.getenv("SITE_URL"))` after writing the processed feed. Add generated files to the workflow commit list. Do not hardcode a GitHub domain; document `SITE_URL` in README.

- [ ] **Step 4: Verify green and commit**

Run: `python -m unittest discover -v && python scripts/processor.py && git add scripts/collector.py scripts/processor.py .github/workflows/update.yml README.md tests && git commit -m "feat: publish generated project catalog artifacts"`

Expected: tests green and processor reports pages and sitemap.

## Task 4: Redesign homepage and link into project pages

**Files:**
- Modify: `index.html`
- Modify: `styles.css`
- Modify: `app.js`
- Create: `tests/app.test.js`

**Interfaces:**
- Consumes: records with `project.path` and existing score/status fields.
- Produces: `escapeHtml(value)`, `projectCard(repo)`, accessible filtering/sorting, safe internal links, and editorial UI.

- [ ] **Step 1: Write a failing DOM-safe card test**

```javascript
test('project card has internal URL and escaped text', () => {
  const markup = projectCard({name: '<Tool>', description: 'Use & share', project: {path: 'project/tool-42/'}, tags: [], commercial_alternatives: [], score: 8, stargazers_count: 1, updated_at: '2026-07-01T00:00:00Z'});
  assert.match(markup, /href="project\/tool-42\/"/);
  assert.match(markup, /&lt;Tool&gt;/);
  assert.doesNotMatch(markup, /<Tool>/);
});
```

- [ ] **Step 2: Verify red**

Run: `node --test tests/app.test.js`

Expected: import/export failure because the helpers do not exist.

- [ ] **Step 3: Implement safe content-first UI**

Extract and export `escapeHtml`, `projectCard`, count/date helpers. Escape every source field before `innerHTML`; external GitHub links use `target="_blank" rel="noreferrer"`. Rebuild HTML with masthead, concise hero, search, signal rail, browse controls, catalog and footer landmarks. Rebuild CSS mobile-first using fluid `clamp()` space/type, 44px controls, visible focus, semantic evidence rows, responsive 640/900/1160px layouts, and `prefers-reduced-motion`.

- [ ] **Step 4: Verify green and prohibited styles absent**

Run: `node --test tests/app.test.js && rg -n 'linear-gradient|backdrop-filter' index.html styles.css`

Expected: test passes and ripgrep has no matches.

- [ ] **Step 5: Commit**

Run: `git add index.html styles.css app.js tests/app.test.js && git commit -m "feat: redesign catalog as editorial tool intelligence"`

## Task 5: Add a static-output audit and perform final verification

**Files:**
- Create: `scripts/verify_site.py`
- Create: `tests/test_verify_site.py`
- Modify: `README.md`

**Interfaces:**
- Produces: `verify_site(root: Path) -> None`, raising `SiteVerificationError` for a missing project page, duplicate path, or absent sitemap entry.

- [ ] **Step 1: Write a failing broken-link test**

Create a temporary `data/processed_repos.json` containing `{ "project": { "path": "project/missing-42/" } }`. Assert `verify_site(tmp_path)` raises `SiteVerificationError` containing `missing-42`.

- [ ] **Step 2: Verify red, implement, and verify green**

Run: `python -m unittest tests.test_verify_site -v` and confirm absent-module failure. Implement path existence, duplicate-path, and sitemap-coverage checks using only `Path` and `json`. Re-run `python -m unittest discover -v` and expect green.

- [ ] **Step 3: Build and audit the real catalog**

Run: `python scripts/processor.py && python scripts/verify_site.py`

Expected: matching catalog/project/sitemap counts and exit code zero.

- [ ] **Step 4: Visual and interaction audit**

Serve locally with `python -m http.server 8000`. Verify search/filter/sort, a project-page link, tab focus, and no horizontal overflow at 320px, 768px, and 1440px. Fix any defect with a new failing test when behavior is testable, then rerun all checks.

- [ ] **Step 5: Final self-review and commit**

Run: `python -m unittest discover -v && node --test tests/app.test.js && python scripts/verify_site.py && git status --short`

Compare the implementation and generated output against the approved design specification. Commit generated artifacts and audit tools only after every check passes.
