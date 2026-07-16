# Open-Source Creators — working notes

A daily-refreshed directory of open-source tools for creators. Static site, no framework, no database. Page generation uses **only the Python standard library**; `requirements.txt` exists for the crawler alone. Keep it that way — added dependencies are a real cost here, not a convenience.

## Architecture in one line

`collector.py` (crawl GitHub) → `processor.py` (score, categorize, map alternatives) → `site_generator.py` (6,000+ static pages) → `build.py` (assemble `dist/`) → Vercel.

## Gotchas that have actually bitten

**`PYTHONPATH=.` is mandatory when running the processor.** `processor.py` does `from scripts.site_generator import build_site`, but `python scripts/processor.py` puts `scripts/` on `sys.path` rather than the repo root. Without it: `ModuleNotFoundError: No module named 'scripts'`. This silently broke the daily job for three nights because it only manifests in CI — locally the processor returns early when `data/raw_repos.json` is absent.

**Deploys to Vercel, not GitHub Pages.** Pages was dropped when the repo went private. The GitHub Action only crawls and commits data; Vercel builds from `main` on every push. Don't re-add Pages steps.

**`GITHUB_TOKEN` in the workflow is GitHub's built-in token**, created per-run automatically. It is a reserved name and cannot be set as a repo secret. A personal token is only needed to run the crawler locally, via a git-ignored `.env` at the repo root, and only needs `public_repo` scope.

**The homepage fetches `data/index.json`, not `processed_repos.json`.** The index is slim build output containing only rendered fields (~900 KB gzipped vs ~1.25 MB). It does not exist until `build.py` runs — serving the repo without building shows the loading-error state.

**Commercial-alternative matching is word-boundary based, deliberately not `\b`.** Python's `\w` spans non-ASCII, so `\bchatgpt\b` fails inside CJK prose like `支持ChatGPT多轮对话`. The ASCII lookarounds in `processor.py` handle this. Raw substring matching caused 53 false claims ("canvas" → Replaces Canva).

## Before committing

```bash
PYTHONPATH=. python -m unittest discover   # 78 tests
python build.py                            # ~7s, 6,000+ pages
python scripts/verify_site.py dist         # page/record parity, dangling links, sitemap
```

`verify_site.py` runs in CI before the data commit, so a broken generation fails loudly instead of shipping.

## Known open items

- **"Mention ≠ replacement":** a repo that merely *mentions* Runway still gets "Replaces Runway". Needs intent detection, not tokenization.
- `dist/` still ships the unused 6.9 MB `processed_repos.json`. Nothing fetches it; it doubles as a de-facto public dataset endpoint.
- Roadmap items in the README are aspirational, not implemented.
- No frontend JS tests.
