<p align="center">
  <a href="https://open-source-creators.vercel.app">
    <img src="docs/banner.svg" alt="Open-Source Creators" width="100%">
  </a>
</p>

<p align="center">
  <a href="https://open-source-creators.vercel.app"><img src="https://img.shields.io/badge/live%20demo-open--source--creators.vercel.app-ffd400?style=flat-square&labelColor=0a0a0a" alt="Live demo"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-ffd400?style=flat-square&labelColor=0a0a0a" alt="MIT License"></a>
  <img src="https://img.shields.io/badge/updated-daily-ffd400?style=flat-square&labelColor=0a0a0a" alt="Updated daily">
  <a href="https://github.com/mostafamohamedAyoussef/Open-Source-Creators/stargazers"><img src="https://img.shields.io/github/stars/mostafamohamedAyoussef/Open-Source-Creators?style=flat-square&labelColor=0a0a0a&color=ffd400" alt="Stars"></a>
</p>

# Open-Source Creators

**A collective of free open-source repos for creators — updated daily.**

Open-Source Creators is a continuously-updated directory of open-source tools for content creators, marketers, filmmakers, and AI builders. It tracks open-source alternatives to commercial giants like **Midjourney, Runway, Jasper, Canva, ElevenLabs, and CapCut** — automatically crawled from GitHub, scored, categorized, and published as a fast static site every day.

### 🔗 Live: **[open-source-creators.vercel.app](https://open-source-creators.vercel.app)**

> ⭐ If this helps you discover great open-source tools, a star goes a long way.

<p align="center">
  <a href="https://open-source-creators.vercel.app">
    <img src="docs/demo.gif" alt="Open-Source Creators demo — search a commercial tool, find free open-source alternatives" width="100%">
  </a>
  <br>
  <em><a href="docs/demo.mp4">▶ Watch the 19s demo with sound</a> · <a href="https://open-source-creators.vercel.app">try it live</a></em>
</p>

---

## Features

- **Automated daily crawl** — a GitHub Action runs the GitHub Search API across 12 creator-focused categories (AI image/video, TTS, video editing, design, automation, 3D, and more), deduplicating by repository ID.
- **Smart scoring** — every repo is scored 1–10 from stars, update recency, description completeness, and topic coverage, with derived signals for *hidden gems* and *emerging* projects.
- **Commercial-alternative mapping** — surfaces which paid product each open-source tool can replace ("Replaces Midjourney", "Replaces CapCut", …).
- **Per-project pages** — a canonical, SEO-ready static page for every one of the ~6,000+ repositories, with facts, tags, commercial alternatives, and deterministically-ranked related projects.
- **Fast, static, dependency-light** — vanilla HTML/CSS/JS frontend; page generation uses only the Python standard library. No client framework, no database.
- **SEO built in** — per-page canonical URLs, Open Graph/Twitter tags, JSON-LD `SoftwareApplication` structured data, and a generated `sitemap.xml`.
- **Accessible & responsive** — semantic landmarks, keyboard-navigable controls, `prefers-reduced-motion`, and a black/white/yellow editorial design that works from 320px up.

## How it works

```
GitHub Search API
        │
        ▼
scripts/collector.py     → data/raw_repos.json      (crawl + dedupe by repo id)
        │
        ▼
scripts/processor.py     → data/processed_repos.json (score, categorize, map alternatives)
        │
        ▼
scripts/site_generator.py → project/<slug>/index.html + data/projects/*.json
                            + sitemap.xml + catalog-meta.json
        │
        ▼
build.py                 → dist/  (assembled static site, deployed to Vercel)
```

The whole pipeline runs daily in GitHub Actions and redeploys automatically on Vercel.

## Local development

**Quickest path — no GitHub token needed.** The dataset is committed, so you can build and serve the whole site straight from it:

```bash
python build.py                        # assembles dist/ (~7s, 6,000+ pages)
cd dist && python -m http.server 8000  # open http://localhost:8000
```

> The homepage fetches the generated `data/index.json` (a slim, minified index — only the fields the page renders). It's build output, so **you must run `build.py` before serving**; opening the site without building shows the loading-error state.

**Full pipeline** (re-crawls GitHub — needs a token):

```bash
pip install -r requirements.txt              # only the collector needs deps
echo "GITHUB_TOKEN=ghp_your_token_here" > .env

python scripts/collector.py                  # crawl GitHub → data/raw_repos.json
PYTHONPATH=. python scripts/processor.py     # score + generate the site
```

> `PYTHONPATH=.` is required: `processor.py` imports `scripts.site_generator`, and running a script puts `scripts/` on `sys.path` rather than the repo root.

**Audit the generated output** (page/record parity, duplicate slugs, dangling related links, sitemap + index integrity):

```bash
python scripts/verify_site.py dist           # exits non-zero on any inconsistency
```

Run the test suite:

```bash
PYTHONPATH=. python -m unittest discover -v
```

## Deployment

The site deploys to **Vercel** from `main`. `vercel.json` runs `python3 build.py`, which assembles a clean `dist/` (static frontend + generated project pages + sitemap) that Vercel serves. Canonical URLs use Vercel's `VERCEL_PROJECT_PRODUCTION_URL` automatically, or set a `SITE_URL` variable to pin a custom domain. The generated output is rebuilt on every deploy and is not committed to git.

## Roadmap

Per-project stable IDs and JSON artifacts are intentional seams for what's next:

- [ ] **Codex-assisted PR review & release automation** in CI
- [ ] **AI-generated project summaries** (one-line "what this does / who it's for")
- [ ] Historical star-growth analytics and trending/fastest-growing views
- [ ] Semantic search over embeddings
- [ ] "Open-source alternatives to X" landing pages
- [ ] Public JSON API + MCP server for AI assistants

## Contributing

Contributions are very welcome — especially new categories, better commercial-alternative mappings, and data-quality fixes. See **[CONTRIBUTING.md](CONTRIBUTING.md)** to get started. Please also read the **[Code of Conduct](CODE_OF_CONDUCT.md)**.

## License

Released under the [MIT License](LICENSE).
