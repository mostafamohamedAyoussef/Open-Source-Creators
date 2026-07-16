import json
import os
import math
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

# Commercial mapping dictionary
COMMERCIAL_MAPPING = {
    "Runway": ["runway", "video-generation", "text-to-video", "video-diffusion"],
    "Higgsfield": ["higgsfield", "video-generation", "cinematic-generation"],
    "Canva": ["canva", "design-tool", "graphic-design"],
    "Adobe Premiere": ["premiere", "video-editing", "non-linear-editor"],
    "CapCut": ["capcut", "video-editing", "tiktok-automation", "shorts"],
    "Midjourney": ["midjourney", "text-to-image", "stable-diffusion", "flux"],
    "Photoshop": ["photoshop", "image-editing", "inpainting", "outpainting", "photopea"],
    "Jasper": ["jasper", "copywriting", "ai-writing"],
    "Copy.ai": ["copy.ai", "copywriting", "ai-writing"],
    "ChatGPT": ["chatgpt", "conversational-ai", "chat-ui", "open-webui"],
    "ElevenLabs": ["elevenlabs", "text-to-speech", "tts", "voice-cloning"],
    "Descript": ["descript", "video-editing", "transcription", "podcast-editing"],
    "Notion": ["notion", "knowledge-management", "productivity"],
    "Figma": ["figma", "design-tool", "ui-design", "ux-design", "penpot"]
}

# A curated list is not a tool. The scoring signals (stars, recency, a complete
# description, rich topics) are exactly what "awesome-*" lists maximise, so without
# a correction they outrank the software they link to: 97 of 180 awesome-* repos
# scored >= 8.0, and poteto/hiring-without-whiteboards — an interview-practices
# list — scored a perfect 10.0 inside "Design Tools".
#
# These repos are kept rather than dropped (awesome-creative-coding is genuinely
# useful to a creator) but capped below any healthy tool, so browsing a category by
# score surfaces software first. They are also tagged so the UI can filter them.
NON_TOOL_SCORE_CAP = 5.0

# Topics a repo uses to self-identify as a reading list / collection.
#
# Kept deliberately narrow. Broader tags produced false positives against the real
# dataset: "directory" flagged backlink-pilot (a tool that submits products TO
# directories) and "reference"/"collection" are used by plenty of working software.
# A false positive caps a real tool at 5.0 and buries it — strictly worse than
# letting one list rank high — so this errs toward precision over recall.
_LIST_TOPICS = frozenset({
    "awesome", "awesome-list", "awesome-lists", "curated-list", "list", "lists",
    "resources",
})

# Topics that mean the repo is educational or career material, not a creator tool.
# Homonyms make this necessary: hiring-without-whiteboards is tagged "whiteboard"
# (as in whiteboard interviews) and so was collected into Design Tools.
_NON_TOOL_TOPICS = frozenset({
    "hiring", "interview", "interviews", "interview-questions", "interview-practice",
    "jobs", "job-search", "career", "careers", "resume", "cv",
    "tutorial", "tutorials", "course", "courses", "book", "books", "ebook",
    "roadmap", "cheatsheet", "cheatsheets", "guide", "guides", "papers",
    "learning", "education", "study", "curriculum", "examples", "boilerplate-list",
})

# Description phrasings that announce a list.
#
# A bare "^list of ..." was tried and rejected: it flagged Matalogue, a real Blender
# addon described as "List of node trees to switch between quickly". These patterns
# require an explicit curation word, so "generate a list of captions" (a tool) and
# "List of node trees" (a tool) both stay clear, while "A curated list of X" is caught.
_LIST_DESC_PATTERNS = tuple(re.compile(p) for p in (
    r"\b(?:curated|awesome|comprehensive|exhaustive|ultimate|definitive)\s+"
    r"(?:and\s+\w+\s+)?(?:list|collection|catalog(?:ue)?|index)\b",
    r"\blist\s+of\s+(?:awesome|free|open[- ]source|useful|the\s+best)\b",
    r"\bcurated\s+(?:list|collection|set)\b",
    r"\bawesome\s+list\b",
))


# Topics by which a repo self-identifies as executable software. These veto a
# topic-only list match, because GitHub topics name a repo's SUBJECT as readily as
# its nature: backlink-pilot is a Playwright automation CLI tagged "awesome-lists"
# because it SUBMITS products TO awesome-lists. Treating that tag as a self-
# description mislabels the tool — the same "mention is not identity" error that
# made a prompt-list claim it "Replaces Runway".
_TOOL_TOPICS = frozenset({
    "cli", "command-line", "automation", "library", "framework", "api", "sdk",
    "plugin", "addon", "extension", "bot", "daemon", "server", "self-hosted",
    "docker", "playwright", "selenium", "electron", "desktop-app", "webapp",
    "generator", "editor", "compiler", "parser", "package", "npm-package",
})


def is_curated_list(repo):
    """True when a repo is a reading list / resource collection rather than a tool.

    Signals, in order of confidence:
      1. The awesome-* naming convention — definitive, not vetoable.
      2. An explicit curation phrase in the description ("A curated list of ...").
      3. Self-identifying topics ("awesome-list", "list", "resources") — but only
         when the repo does NOT also claim to be software (see _TOOL_TOPICS), since
         a topic can name what a tool acts on rather than what it is.
    """
    name = str(repo.get("name", "")).lower()
    if name.startswith("awesome-") or name == "awesome":
        return True

    desc = str(repo.get("description") or "").lower()
    if any(p.search(desc) for p in _LIST_DESC_PATTERNS):
        return True

    topics = {str(t).lower() for t in repo.get("topics", [])}
    return bool(topics & _LIST_TOPICS) and not (topics & _TOOL_TOPICS)


def is_non_tool(repo):
    """True when a repo is educational/career material rather than a creator tool."""
    topics = {str(t).lower() for t in repo.get("topics", [])}
    return bool(topics & _NON_TOOL_TOPICS)


def calculate_score(repo):
    stars = repo.get("stargazers_count", 0)
    score = min(math.log10(max(stars, 1)) * 1.5, 6.0) # Up to 6 points from stars
    
    # Activity score
    now = datetime.now(timezone.utc)
    updated = datetime.fromisoformat(repo.get("updated_at").replace('Z', '+00:00'))
    days_since_update = (now - updated).days
    
    if days_since_update <= 30:
        score += 2.0
    elif days_since_update <= 90:
        score += 1.5
    elif days_since_update <= 180:
        score += 1.0
    elif days_since_update <= 365:
        score += 0.5
        
    # Documentation / Description
    if repo.get("description"):
        score += 1.0
        
    # Topics/Tags presence
    if len(repo.get("topics", [])) > 0:
        score += 1.0
        
    return round(min(score, 10.0), 1)

# A "word" character for boundary purposes is an ASCII letter/digit only.
# We deliberately avoid re's \b, whose \w includes non-ASCII letters: \b would
# fail to match "ChatGPT" inside CJK prose such as "支持ChatGPT多轮对话" because
# there is no boundary between two word characters. Lookarounds restricted to
# ASCII alphanumerics treat CJK (and punctuation, whitespace, "-", "_", "/")
# as boundaries, so "rag-based" and "ChatGPT多轮" match while "storage",
# "dragging", "canvas" and "description" do not.
_BOUNDARY_LEFT = r"(?<![a-z0-9])"
_BOUNDARY_RIGHT = r"(?![a-z0-9])"


@lru_cache(maxsize=None)
def _keyword_regex(keyword):
    """Compile a word-boundary matcher for one keyword.

    Cached, so each distinct keyword is compiled exactly once for the whole
    process rather than once per repository.

    Keywords are matched literally (``re.escape``) so dotted keywords such as
    "copy.ai" cannot have their "." act as a regex wildcard. Multi-word
    keywords ("adobe audition") tolerate any run of whitespace between words;
    hyphenated keywords ("text-to-image") are matched in their literal
    hyphenated form.
    """
    body = r"\s+".join(re.escape(part) for part in keyword.lower().split(" ") if part)
    return re.compile(_BOUNDARY_LEFT + body + _BOUNDARY_RIGHT)


def map_commercial_alternative(repo):
    """Map a repo to the commercial products it can replace.

    Topics are exact tags, so they are compared by exact set membership.
    Descriptions are free prose, so they are matched on word boundaries to
    avoid claims like "Replaces Canva" for an "infinite canvas" library.
    """
    topics = set(repo.get("topics", []))
    desc = str(repo.get("description", "")).lower()

    alternatives = []
    for commercial, keywords in COMMERCIAL_MAPPING.items():
        if any(kw in topics for kw in keywords) or any(
            _keyword_regex(kw).search(desc) for kw in keywords
        ):
            alternatives.append(commercial)

    return alternatives

def process_repos(root_dir=None):
    root = Path(root_dir) if root_dir else Path(__file__).resolve().parent.parent
    data_dir = root / "data"
    raw_path = data_dir / "raw_repos.json"
    if not raw_path.exists():
        print("raw_repos.json not found")
        return

    with open(raw_path, 'r', encoding='utf-8') as f:
        repos = json.load(f)

    processed = []
    for repo in repos:
        repo['score'] = calculate_score(repo)
        repo['commercial_alternatives'] = map_commercial_alternative(repo)

        # A list about tools, or a career/learning resource, is not a creator tool.
        # Cap it below any healthy tool so category browsing surfaces software first.
        repo['is_curated_list'] = is_curated_list(repo)
        repo['is_non_tool'] = is_non_tool(repo)
        if repo['is_curated_list'] or repo['is_non_tool']:
            repo['score'] = min(repo['score'], NON_TOOL_SCORE_CAP)
            # A list cannot "replace Midjourney" — it only links to things that might.
            repo['commercial_alternatives'] = []

        all_tags = set(repo.get("topics", []))
        all_tags.update([cat.lower() for cat in repo.get("categories", [])])
        if repo['is_curated_list']:
            all_tags.add("list")
        repo['tags'] = list(all_tags)

        now = datetime.now(timezone.utc)
        created = datetime.fromisoformat(repo.get("created_at").replace('Z', '+00:00'))
        age_days = (now - created).days

        repo['is_hidden_gem'] = (
            repo.get('stargazers_count', 0) < 5000 and
            repo['score'] >= 7.5
        )

        repo['is_emerging'] = (
            age_days <= 730 and
            repo['stargazers_count'] > 1000 and
            repo['score'] >= 8.0
        )

        processed.append(repo)

    processed.sort(key=lambda x: (x['score'], x['stargazers_count']), reverse=True)

    out_path = data_dir / "processed_repos.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(processed, f, indent=2, ensure_ascii=False)

    print(f"Processed {len(processed)} repositories.")
    print(f"Saved to {out_path}")

    from scripts.site_generator import build_site
    site_url = os.getenv("SITE_URL")
    metadata = build_site(processed, root, site_url)
    print(f"Generated {metadata['total_projects']} project pages.")

if __name__ == "__main__":
    process_repos()
