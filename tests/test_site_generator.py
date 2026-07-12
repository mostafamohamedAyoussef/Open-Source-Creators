import unittest

from scripts.site_generator import (
    build_project_record,
    make_project_slug,
    rank_related_projects,
)


class SiteGeneratorTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
