import json
import random
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.site_generator import (
    INDEX_FIELDS,
    RelatedIndex,
    build_index_entry,
    build_site,
    build_project_record,
    make_project_slug,
    rank_related_projects,
)


def naive_rank_related_projects(project, candidates, limit=6):
    """Reference implementation the optimized ranking must match exactly."""
    project_categories = set(project.get("categories") or [])
    project_tags = set(project.get("tags") or [])
    project_alternatives = set(project.get("commercial_alternatives") or [])
    project_language = project.get("language")

    def relevance(candidate):
        return (
            3 * len(project_categories & set(candidate.get("categories") or []))
            + 2 * len(project_tags & set(candidate.get("tags") or []))
            + 2
            * len(
                project_alternatives
                & set(candidate.get("commercial_alternatives") or [])
            )
            + int(bool(project_language) and candidate.get("language") == project_language)
        )

    related = [c for c in candidates if c.get("id") != project.get("id")]
    related.sort(
        key=lambda c: (relevance(c), c.get("score", 0), c.get("stargazers_count", 0)),
        reverse=True,
    )
    return related[:limit]


class SiteGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_build_site_writes_escaped_page_json_and_sitemap(self):
        repos = [{"id": 42, "full_name": "Acme/Creative Tool", "name": "Creative <Tool>", "description": "Use & share", "categories": ["Audio"], "tags": ["tts"], "commercial_alternatives": [], "language": "Python", "license": "MIT", "stargazers_count": 1, "forks_count": 2, "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-07-01T00:00:00Z", "html_url": "https://github.com/acme/tool", "score": 8}]
        build_site(repos, self.root, "https://example.github.io/catalog")
        self.assertIn("Creative &lt;Tool&gt;", (self.root / "project/acme-creative-tool-42/index.html").read_text())
        self.assertTrue((self.root / "data/projects/acme-creative-tool-42.json").exists())

    def test_build_site_handles_missing_optional_metadata(self):
        repos = [{"id": 42, "name": "Minimal", "categories": None, "tags": None, "commercial_alternatives": None}]

        build_site(repos, self.root)

        self.assertTrue((self.root / "project/minimal-42/index.html").exists())

    # --- Regression tests: nullable / missing / empty metadata ---

    def test_build_project_record_normalizes_none_to_empty_lists(self):
        repo = {"id": 1, "name": "Test", "categories": None, "tags": None, "commercial_alternatives": None}
        record = build_project_record(repo, "2026-07-12T00:00:00Z")
        self.assertEqual(record["categories"], [])
        self.assertEqual(record["tags"], [])
        self.assertEqual(record["commercial_alternatives"], [])

    def test_build_project_record_normalizes_missing_keys_to_empty_lists(self):
        repo = {"id": 2, "name": "Bare"}
        record = build_project_record(repo, "2026-07-12T00:00:00Z")
        self.assertEqual(record["categories"], [])
        self.assertEqual(record["tags"], [])
        self.assertEqual(record["commercial_alternatives"], [])

    def test_build_project_record_preserves_populated_lists(self):
        repo = {"id": 3, "name": "Full", "categories": ["Audio"], "tags": ["tts"], "commercial_alternatives": ["Audition"]}
        record = build_project_record(repo, "2026-07-12T00:00:00Z")
        self.assertEqual(record["categories"], ["Audio"])
        self.assertEqual(record["tags"], ["tts"])
        self.assertEqual(record["commercial_alternatives"], ["Audition"])

    def test_build_project_record_preserves_empty_lists(self):
        repo = {"id": 4, "name": "Empty", "categories": [], "tags": [], "commercial_alternatives": []}
        record = build_project_record(repo, "2026-07-12T00:00:00Z")
        self.assertEqual(record["categories"], [])
        self.assertEqual(record["tags"], [])
        self.assertEqual(record["commercial_alternatives"], [])

    def test_rank_related_handles_none_categories(self):
        project = {"id": 1, "categories": None}
        candidates = [project, {"id": 2, "categories": ["Audio"]}]
        related = rank_related_projects(project, candidates)
        self.assertEqual([c["id"] for c in related], [2])

    def test_rank_related_handles_none_tags(self):
        project = {"id": 1, "tags": None}
        candidates = [project, {"id": 2, "tags": ["tts"]}]
        related = rank_related_projects(project, candidates)
        self.assertEqual([c["id"] for c in related], [2])

    def test_rank_related_handles_none_commercial_alternatives(self):
        project = {"id": 1, "commercial_alternatives": None}
        candidates = [project, {"id": 2, "commercial_alternatives": ["Audition"]}]
        related = rank_related_projects(project, candidates)
        self.assertEqual([c["id"] for c in related], [2])

    def test_rank_related_handles_missing_keys(self):
        project = {"id": 1}
        candidates = [project, {"id": 2}]
        related = rank_related_projects(project, candidates)
        self.assertEqual([c["id"] for c in related], [2])

    def test_rank_related_handles_empty_lists(self):
        project = {"id": 1, "categories": [], "tags": [], "commercial_alternatives": []}
        candidates = [project, {"id": 2, "categories": [], "tags": [], "commercial_alternatives": []}]
        related = rank_related_projects(project, candidates)
        self.assertEqual([c["id"] for c in related], [2])

    def test_build_site_with_missing_keys(self):
        repos = [{"id": 10, "name": "NoKeys"}]
        build_site(repos, self.root)
        self.assertTrue((self.root / "project/nokeys-10/index.html").exists())

    def test_build_site_with_empty_lists(self):
        repos = [{"id": 11, "name": "EmptyLists", "categories": [], "tags": [], "commercial_alternatives": []}]
        build_site(repos, self.root)
        self.assertTrue((self.root / "project/emptylists-11/index.html").exists())

    def test_build_site_with_populated_lists(self):
        repos = [{"id": 12, "name": "Populated", "categories": ["Video"], "tags": ["editor"], "commercial_alternatives": ["Premiere"]}]
        build_site(repos, self.root)
        page = (self.root / "project/populated-12/index.html").read_text()
        self.assertIn("Video", page)
        self.assertIn("editor", page)
        self.assertIn("Premiere", page)

    def test_slug_is_stable_and_normalized(self):
        self.assertEqual(
            make_project_slug({"id": 42, "full_name": "Acme/Creative Tool!"}),
            "acme-creative-tool-42",
        )

    def test_record_does_not_mutate_source(self):
        source = {"id": 42, "full_name": "Acme/Creative Tool!"}

        record = build_project_record(source, "2026-07-12T00:00:00Z")

        self.assertEqual(record["project"]["path"], "project/acme-creative-tool-42/")
        self.assertNotIn("project", source)

    def test_related_projects_prioritize_shared_categories_and_exclude_current(self):
        project = {
            "id": 1,
            "categories": ["Audio"],
            "tags": ["tts"],
            "commercial_alternatives": [],
            "language": "Python",
        }
        candidates = [
            project,
            {
                "id": 2,
                "categories": [],
                "tags": [],
                "commercial_alternatives": [],
                "language": "Python",
                "stargazers_count": 1000,
            },
            {
                "id": 3,
                "categories": ["Audio"],
                "tags": ["tts"],
                "commercial_alternatives": [],
                "language": "JavaScript",
                "stargazers_count": 1,
            },
        ]

        related = rank_related_projects(project, candidates)

        self.assertEqual([candidate["id"] for candidate in related], [3, 2])

    def test_related_projects_break_relevance_ties_by_existing_score(self):
        project = {"id": 1, "categories": ["Audio"], "language": "Python"}
        candidates = [
            project,
            {
                "id": 2,
                "categories": ["Audio"],
                "score": 1,
                "stargazers_count": 1000,
            },
            {
                "id": 3,
                "categories": ["Audio"],
                "score": 9,
                "stargazers_count": 1,
            },
        ]

        related = rank_related_projects(project, candidates)

        self.assertEqual([candidate["id"] for candidate in related], [3, 2])

    def test_related_projects_do_not_match_missing_languages(self):
        project = {"id": 1}
        candidates = [
            project,
            {"id": 2, "score": 1, "stargazers_count": 1},
            {"id": 3, "language": "Python", "score": 9, "stargazers_count": 1},
        ]

        related = rank_related_projects(project, candidates)

        self.assertEqual([candidate["id"] for candidate in related], [3, 2])

    def test_related_projects_weight_shared_commercial_alternatives_above_language(self):
        project = {
            "id": 1,
            "commercial_alternatives": ["Adobe Audition"],
            "language": "Python",
        }
        candidates = [
            project,
            {
                "id": 2,
                "commercial_alternatives": [],
                "language": "Python",
                "score": 9,
                "stargazers_count": 1000,
            },
            {
                "id": 3,
                "commercial_alternatives": ["Adobe Audition"],
                "language": "JavaScript",
                "score": 1,
                "stargazers_count": 1,
            },
        ]

        related = rank_related_projects(project, candidates)

        self.assertEqual([candidate["id"] for candidate in related], [3, 2])

    def test_related_projects_respects_default_and_explicit_limits(self):
        project = {"id": 1, "categories": ["Audio"]}
        candidates = [project] + [
            {"id": candidate_id, "categories": ["Audio"], "score": 10 - candidate_id}
            for candidate_id in range(2, 10)
        ]

        default_related = rank_related_projects(project, candidates)
        limited_related = rank_related_projects(project, candidates, limit=2)

        self.assertEqual(
            [candidate["id"] for candidate in default_related], [2, 3, 4, 5, 6, 7]
        )
        self.assertEqual([candidate["id"] for candidate in limited_related], [2, 3])


class HomepageIndexTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.repo = {
            "id": 42,
            "full_name": "Acme/Tool",
            "name": "Tool",
            "description": "Edits video",
            "html_url": "https://github.com/acme/tool",
            "stargazers_count": 1200,
            "forks_count": 300,
            "language": "Python",
            "updated_at": "2026-07-01T00:00:00Z",
            "created_at": "2026-01-01T00:00:00Z",
            "license": "MIT License",
            "topics": ["video", "editor"],
            "categories": ["Video"],
            "score": 9.5,
            "commercial_alternatives": ["Premiere"],
            "tags": ["video", "editor"],
            "is_hidden_gem": False,
            "is_emerging": True,
        }

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _index(self):
        build_site([self.repo], self.root)
        return json.loads((self.root / "data" / "index.json").read_text())

    def test_index_entry_keeps_every_field_the_homepage_renders(self):
        entry = self._index()[0]
        self.assertEqual(entry["name"], "Tool")
        self.assertEqual(entry["description"], "Edits video")
        self.assertEqual(entry["stargazers_count"], 1200)
        self.assertEqual(entry["score"], 9.5)
        self.assertEqual(entry["updated_at"], "2026-07-01T00:00:00Z")
        self.assertEqual(entry["categories"], ["Video"])
        self.assertEqual(entry["tags"], ["video", "editor"])
        self.assertEqual(entry["commercial_alternatives"], ["Premiere"])
        self.assertEqual(entry["html_url"], "https://github.com/acme/tool")
        self.assertEqual(entry["path"], "project/acme-tool-42/")

    def test_index_entry_drops_fields_the_homepage_never_reads(self):
        entry = self._index()[0]
        for dropped in (
            "topics",
            "forks_count",
            "created_at",
            "license",
            "language",
            "full_name",
            "id",
            "is_hidden_gem",
            "is_emerging",
            "project",
            "related_projects",
        ):
            self.assertNotIn(dropped, entry)

    def test_index_entry_allows_only_known_keys(self):
        allowed = set(INDEX_FIELDS) | {"path"}
        self.assertLessEqual(set(self._index()[0]), allowed)

    def test_index_is_minified(self):
        build_site([self.repo], self.root)
        raw = (self.root / "data" / "index.json").read_text()
        self.assertNotIn("\n", raw)
        self.assertNotIn(", ", raw)
        self.assertNotIn(": ", raw)

    def test_index_has_one_entry_per_repo_in_source_order(self):
        second = dict(self.repo, id=43, name="Other", full_name="Acme/Other")
        build_site([self.repo, second], self.root)
        entries = json.loads((self.root / "data" / "index.json").read_text())
        self.assertEqual([e["name"] for e in entries], ["Tool", "Other"])

    def test_index_omits_empty_and_missing_optional_fields(self):
        entry = build_index_entry(
            {"name": "Bare", "description": None, "categories": [], "tags": None}
        )
        self.assertEqual(entry, {"name": "Bare"})

    def test_index_entry_survives_repos_with_missing_metadata(self):
        build_site([{"id": 7, "name": "Minimal"}], self.root)
        entries = json.loads((self.root / "data" / "index.json").read_text())
        self.assertEqual(entries, [{"name": "Minimal", "path": "project/minimal-7/"}])

    def test_index_is_smaller_than_the_full_dataset(self):
        build_site([self.repo], self.root)
        slim = (self.root / "data" / "index.json").stat().st_size
        full = len(json.dumps([self.repo], indent=2))
        self.assertLess(slim, full)


class RankingEquivalenceTests(unittest.TestCase):
    """The index-backed ranking must match the naive scan exactly."""

    def _assert_matches_naive(self, repos, limit=6):
        index = RelatedIndex(repos)
        for project in repos:
            expected = [id(c) for c in naive_rank_related_projects(project, repos, limit)]
            actual = [id(c) for c in rank_related_projects(project, repos, limit, index)]
            self.assertEqual(expected, actual, f"mismatch for project {project.get('id')}")

    def test_matches_naive_on_generated_corpus(self):
        random.seed(1234)
        categories = ["Audio", "Video", "Image", "3D", "Writing"]
        tags = [f"tag{i}" for i in range(12)]
        alternatives = ["Premiere", "Canva", "Runway", "ElevenLabs"]
        languages = ["Python", "JavaScript", "Rust", None]
        repos = [
            {
                "id": i,
                "name": f"repo{i}",
                "categories": random.sample(categories, random.randint(0, 2)),
                "tags": random.sample(tags, random.randint(0, 4)),
                "commercial_alternatives": random.sample(
                    alternatives, random.randint(0, 2)
                ),
                "language": random.choice(languages),
                # Deliberately coarse so relevance/score/star ties are common.
                "score": random.randint(0, 3),
                "stargazers_count": random.choice([0, 1, 5]),
            }
            for i in range(220)
        ]
        for limit in (1, 6, 20):
            self._assert_matches_naive(repos, limit)

    def test_matches_naive_when_nothing_is_shared(self):
        repos = [
            {"id": 1, "language": "Python", "score": 1, "stargazers_count": 1},
            {"id": 2, "language": "Python", "score": 1, "stargazers_count": 1},
            {"id": 3, "language": "Rust", "score": 1, "stargazers_count": 1},
            {"id": 4, "score": 1, "stargazers_count": 1},
        ]
        self._assert_matches_naive(repos)

    def test_matches_naive_with_null_and_missing_metadata(self):
        repos = [
            {"id": 1, "categories": None, "tags": None, "commercial_alternatives": None},
            {"id": 2},
            {"id": 3, "categories": [], "tags": [], "language": None},
            {"id": 4, "categories": ["Audio"], "language": "Python", "score": 5},
        ]
        self._assert_matches_naive(repos)

    def test_language_only_candidates_outrank_unrelated_but_lose_to_shared_tags(self):
        project = {"id": 1, "tags": ["tts"], "language": "Python"}
        candidates = [
            project,
            {"id": 2, "language": "Python", "score": 10, "stargazers_count": 9999},
            {"id": 3, "tags": ["tts"], "language": "Rust", "score": 0},
            {"id": 4, "score": 10, "stargazers_count": 9999},
        ]
        related = rank_related_projects(project, candidates)
        self.assertEqual([c["id"] for c in related], [3, 2, 4])

    def test_zero_relevance_fallback_fills_the_list(self):
        project = {"id": 1, "categories": ["Audio"]}
        candidates = [project] + [
            {"id": i, "score": i, "stargazers_count": 0} for i in range(2, 6)
        ]
        related = rank_related_projects(project, candidates)
        self.assertEqual([c["id"] for c in related], [5, 4, 3, 2])

    def test_index_backed_ranking_matches_unindexed_calls(self):
        repos = [
            {"id": 1, "categories": ["Audio"], "language": "Python", "score": 3},
            {"id": 2, "categories": ["Audio"], "language": "Python", "score": 5},
            {"id": 3, "tags": ["x"], "score": 1},
        ]
        index = RelatedIndex(repos)
        for project in repos:
            self.assertEqual(
                [c["id"] for c in rank_related_projects(project, repos)],
                [c["id"] for c in rank_related_projects(project, repos, 6, index)],
            )


if __name__ == "__main__":
    unittest.main()
