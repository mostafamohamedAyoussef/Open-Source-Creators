# Open-Source Content Creation Directory

This is an automated, continuously updating directory of the best open-source tools for content creators, marketers, filmmakers, and AI enthusiasts. 

It was built to track open-source alternatives to commercial giants like Midjourney, Runway, Jasper, Canva, ElevenLabs, and more.

## Features

- **Automated Crawling:** Python scripts utilize the GitHub Search API to continuously find and scrape repositories across categories like Video Generation, TTS, AI Agents, and Design.
- **Smart Scoring:** Repositories are automatically scored (1-10) based on their GitHub stars, recency of updates, and completeness of documentation.
- **Daily Updates:** A GitHub Action runs every night at midnight UTC to keep the dataset perfectly up-to-date and to deploy the newest version to GitHub Pages.
- **Beautiful UI:** A responsive, modern frontend built with vanilla HTML/JS/CSS to search, filter, and sort through the massive database.

## Architecture

* `scripts/collector.py`: Fetches raw data from the GitHub API using your Personal Access Token.
* `scripts/processor.py`: Filters, categorizes, maps commercial alternatives, and calculates scores.
* `data/processed_repos.json`: The compiled database used by the frontend.
* `index.html` & `app.js`: The frontend interface.

## Local Setup

If you want to run or test the directory locally:

1. **Install Python Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Add Your GitHub Token (Local Only):**
   Create a `.env` file in the root of the project with your GitHub Personal Access Token (PAT):
   ```
   GITHUB_TOKEN=ghp_your_actual_token_here
   ```

3. **Run the Data Pipeline:**
   ```bash
   python scripts/collector.py
   python scripts/processor.py
   ```

4. **Serve the Frontend:**
   You must use a local server to view the frontend due to CORS restrictions with fetching local JSON files.
   ```bash
   python -m http.server 8000
   ```
   Then open `http://localhost:8000` in your browser.

## Deploying to GitHub Pages

1. Push this code to a public repository on your GitHub account.
2. Navigate to your repository's **Settings > Secrets and variables > Actions**.
3. Create a new repository secret named `GITHUB_TOKEN` and paste your GitHub Personal Access Token.
4. Navigate to **Settings > Pages** and ensure it is enabled (the GitHub Action will handle the deployment automatically).

## Contributing

The categories and commercial mappings are hardcoded inside `scripts/collector.py` and `scripts/processor.py`. Feel free to open a PR to expand the search topics or map new commercial tools!
