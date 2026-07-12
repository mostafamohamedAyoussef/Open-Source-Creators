import re
from copy import deepcopy


def make_project_slug(repo: dict) -> str:
    raw = str(repo.get("full_name") or repo.get("name") or "project").lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", raw).strip("-") or "project"
    return f"{normalized}-{repo['id']}"


def build_project_record(repo: dict, generated_at: str) -> dict:
    record = deepcopy(repo)
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
    project_categories = set(project.get("categories", []))
    project_tags = set(project.get("tags", []))
    project_alternatives = set(project.get("commercial_alternatives", []))
    project_language = project.get("language")

    def relevance(candidate: dict) -> int:
        shared_categories = len(project_categories & set(candidate.get("categories", [])))
        shared_tags = len(project_tags & set(candidate.get("tags", [])))
        shared_alternatives = len(
            project_alternatives & set(candidate.get("commercial_alternatives", []))
        )
        same_language = candidate.get("language") == project_language
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
        key=lambda candidate: (relevance(candidate), candidate.get("stargazers_count", 0)),
        reverse=True,
    )
    return related[:limit]
