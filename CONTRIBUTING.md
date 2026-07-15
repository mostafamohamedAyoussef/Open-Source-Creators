# Contributing to Open-Source Creators

Thanks for helping build the largest open directory of open-source creator tools! Contributions of every size are welcome.

## Ways to contribute

- **Add or refine categories** — the search topics live in `SEARCH_QUERIES` in [`scripts/collector.py`](scripts/collector.py). Add GitHub topics that surface more creator tools.
- **Map commercial alternatives** — extend `COMMERCIAL_MAPPING` in [`scripts/processor.py`](scripts/processor.py) so tools show the paid product they can replace.
- **Improve scoring / data quality** — tune `calculate_score`, fix mis-categorized repos, or improve normalization.
- **Frontend & accessibility** — the UI is vanilla HTML/CSS/JS (`index.html`, `styles.css`, `app.js`) and the project-page template in `scripts/site_generator.py`.
- **Docs & bug reports** — open an issue for anything unclear or broken.

## Development setup

```bash
pip install -r requirements.txt
echo "GITHUB_TOKEN=ghp_your_token_here" > .env   # local only, never commit
python scripts/collector.py
python scripts/processor.py
python -m http.server 8000
```

## Before you open a pull request

1. **Run the tests** — they must pass:
   ```bash
   PYTHONPATH=. python -m unittest discover -v
   ```
2. **Add tests** for new generation logic (see [`tests/test_site_generator.py`](tests/test_site_generator.py) for the style).
3. Keep the frontend dependency-free and the generator standard-library-only.
4. Never commit secrets. `GITHUB_TOKEN` is provided via env / GitHub Actions — the `.env` file is git-ignored.
5. Write a clear PR description explaining the *why*, not just the *what*.

## Commit style

Conventional-commit prefixes are appreciated (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`) but not required.

By contributing, you agree that your contributions are licensed under the project's [MIT License](LICENSE).
