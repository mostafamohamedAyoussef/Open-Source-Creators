import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.site_generator import (
    build_site,
    build_project_record,
    make_project_slug,
    rank_related_projects,
)


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


if __name__ == "__main__":
    unittest.main()
