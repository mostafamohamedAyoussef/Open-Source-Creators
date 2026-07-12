# Project Pages & Editorial Directory Design

## Goal

Evolve the static Open-Source Content Creation Directory from a single searchable list into a polished, indexable directory with a canonical page for every project. The first release must feel like premium creative-tool intelligence while preserving GitHub Pages deployment and the existing daily GitHub ingestion workflow.

## Scope

This release delivers two tightly connected outcomes:

1. A generated, static `/project/<slug>/` page for every processed repository.
2. A redesigned, responsive homepage and project-page visual system in an editorial-intelligence style.

Historical analytics, semantic search, generated prose, screenshots, account features, and an API/MCP server are explicitly out of scope. The data shape will leave room for them without creating a premature database dependency.

## Experience Direction

The visual language is **editorial intelligence**: a warm-paper canvas, near-ink text, cobalt functional accents, and restrained amber status signals. A distinctive display serif for headings pairs with a workhorse sans for data. It should establish credibility through hierarchy, spacing, typography, and transparent data signals rather than decorative effects, glassmorphism, gradients, or unverified claims.

### Homepage

- A compact masthead gives the directory a recognizable identity and anchors a link back to the catalog.
- The hero frames the catalog as a way to find open-source creator tools, with a prominent search field and a concise trust statement based only on available data.
- Discovery controls retain category filtering and sorting, but receive accessible labels, keyboard-friendly controls, and stronger grouping.
- A curated signal strip surfaces existing reliable fields: highest scoring, recently updated, hidden gems, and emerging projects. It does not claim real-time trend calculations.
- Repository cards become internal links to project pages. Their evidence-led layout uses a score/rank column, project name and description, discovery tags, and source facts separated by fine rules rather than floating glass cards. They retain an explicit GitHub outbound link so users can still jump directly to source.
- Each card exposes only useful, reliable facts: score, stars, language, update date, category, tags, and commercial-alternative context where present.

### Project Page

Each generated page is a standalone research brief for one repository. It includes:

- Project identity: name, description, categories, GitHub link, score, and project status signals.
- Facts panel: stars, forks, primary language, license, created date, last updated date, and canonical repository URL.
- Discovery context: tags, commercial products it may replace, and related projects.
- A straightforward use/installation section that links to the repository README rather than presenting a potentially stale invented installation guide.
- A related-project section derived deterministically from shared categories, tags, language, and commercial alternatives. The algorithm must be explainable and must exclude the current project.
- Breadcrumb navigation to the homepage and a visible last-data-refresh timestamp.

## Data & Generation Architecture

The Python processor remains the source of truth for normalized project records. A new static-site build step transforms the processed data into:

- `data/projects/<slug>.json`: one normalized public record per project.
- `project/<slug>/index.html`: a fully rendered canonical project page per project.
- `sitemap.xml`: includes the homepage and all project pages.
- `data/catalog-meta.json`: generated-at timestamp and total project count for the frontend.

Project identity is stable and anchored to the GitHub numeric repository ID. Slugs are generated from the repository full name and ID, so renames do not cause collisions. Existing list data remains in `data/processed_repos.json` for backward compatibility with the homepage.

Every record gains a `project` object with a stable ID, slug, `path`, and generated timestamp. Project records carry normalized fields already collected today; missing values render as an em dash or an omitted section instead of fabricated content.

The processor will also assign an explainable related-project list. Candidate repositories receive points for shared category, tag, language, and commercial-alternative mapping. Ties resolve by the existing score and stars. The generated page labels this as “Related projects” without claiming behavioral personalization.

## SEO & Static Deployment

- Each generated project page has a unique `<title>`, meta description, canonical URL expressed as a relative site path, and Open Graph title/description.
- The build creates a sitemap that uses a configurable public site URL. When no site URL is configured, it still creates valid relative project files and omits absolute canonical/sitemap locations rather than guessing a domain.
- The GitHub Action runs the processor and static-site build before committing generated JSON, project pages, and sitemap. Pages continues to deploy the repository root artifact.
- All internal URLs are relative, allowing both local testing and GitHub Pages project-site deployments.

## Accessibility & Responsiveness

- Semantic landmarks, one `h1` per page, descriptive link labels, visible focus states, and sufficient color contrast are required.
- Layouts must work at 320px wide without horizontal scrolling. Data grids collapse to readable stacked rows on small screens.
- Hover effects are supplementary; every project card and action remains usable by keyboard and touch.
- The interface respects `prefers-reduced-motion`.
- Controls have a 44px minimum target size, spacing and type use fluid `clamp()` values, and breakpoints are content-led around 640px, 900px, and 1160px.

## Error Handling

- The homepage continues to show an actionable loading error when catalog JSON cannot be fetched.
- A generated project page is self-contained and does not require a client-side JSON fetch to render its primary content.
- Invalid or missing optional repository fields never halt the build. The build logs which records are incomplete and produces the remaining pages.
- Slug collisions are prevented by including the repository ID; a duplicate generated path is a build error.

## Verification

- Automated Python tests cover slug generation, project-record serialization, related-project ranking, page rendering with special characters, sitemap generation, and handling missing optional metadata.
- The test suite runs before generated outputs are committed in local development and in GitHub Actions.
- A local static-server smoke test confirms homepage links resolve to generated project pages and that the sitemap references them.

## Deferred Extensions

The stable ID and per-project JSON artifacts are intentional seams for later additions: daily snapshots, stars/forks history, AI-reviewed summaries, screenshots, semantic embeddings, comparison tables, an API, and an MCP server. None of those features is required for this release.
