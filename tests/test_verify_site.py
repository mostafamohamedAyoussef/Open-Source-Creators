"""Tests for the static-output auditor.

Each defect test starts from a real, known-good site built by `build_site`,
injects exactly one regression, and asserts the verifier fails *and* names the
offender. Testing the failures is the point: a verifier that only passes on good
input is worthless.
"""

import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.site_generator import build_site
from scripts.verify_site import (
    REQUIRED_ASSETS,
    main,
    slug_from_path,
    verify_site,
)

SITE_URL = "https://example.com"

REPOS = [
    {
        "id": 1,
        "name": "alpha",
        "full_name": "acme/alpha",
        "description": "Alpha tool",
        "html_url": "https://github.com/acme/alpha",
        "stargazers_count": 500,
        "forks_count": 10,
        "score": 9.0,
        "language": "Python",
        "license": "MIT",
        "created_at": "2020-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "categories": ["video"],
        "tags": ["editor"],
        "commercial_alternatives": ["Premiere"],
    },
    {
        "id": 2,
        "name": "beta",
        "full_name": "acme/beta",
        "description": "Beta tool",
        "html_url": "https://github.com/acme/beta",
        "stargazers_count": 400,
        "forks_count": 8,
        "score": 8.0,
        "language": "Python",
        "license": "MIT",
        "created_at": "2020-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "categories": ["video"],
        "tags": ["editor"],
        "commercial_alternatives": ["Premiere"],
    },
    {
        "id": 3,
        "name": "gamma",
        "full_name": "acme/gamma",
        "description": "Gamma tool",
        "html_url": "https://github.com/acme/gamma",
        "stargazers_count": 300,
        "forks_count": 5,
        "score": 7.0,
        "language": "Rust",
        "license": "Apache-2.0",
        "created_at": "2021-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "categories": ["audio"],
        "tags": ["daw"],
        "commercial_alternatives": ["Ableton"],
    },
]


class VerifySiteTestCase(unittest.TestCase):
    """Base class providing a freshly built, known-good site per test."""

    site_url = SITE_URL

    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        build_site(REPOS, self.root, self.site_url)
        for name in REQUIRED_ASSETS:
            (self.root / name).write_text(f"/* {name} */", encoding="utf-8")

    def assertPasses(self):
        report = verify_site(self.root)
        self.assertTrue(
            report.ok, f"expected a clean site, got failures: {report.failures}"
        )
        return report

    def assertFailsWith(self, *needles):
        report = verify_site(self.root)
        self.assertFalse(report.ok, "expected the verifier to fail, but it passed")
        blob = "\n".join(report.failures)
        for needle in needles:
            self.assertIn(needle, blob, f"failure message missing {needle!r}:\n{blob}")
        return report

    def read_json(self, relative):
        return json.loads((self.root / relative).read_text(encoding="utf-8"))

    def write_json(self, relative, payload):
        (self.root / relative).write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )


class HappyPathTests(VerifySiteTestCase):
    def test_good_site_passes(self):
        report = self.assertPasses()
        self.assertEqual(report.counts["pages on disk"], len(REPOS))
        self.assertEqual(report.counts["index.json entries"], len(REPOS))
        # 6 related links requested per page, but only 2 other projects exist.
        self.assertEqual(report.counts["related links checked"], len(REPOS) * 2)

    def test_good_site_exits_zero(self):
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main([str(self.root), "--quiet"]), 0)
        self.assertIn("OK", out.getvalue())

    def test_defective_site_exits_nonzero(self):
        (self.root / "data" / "index.json").unlink()
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main([str(self.root)]), 1)
        self.assertIn("data/index.json is missing", out.getvalue())

    def test_missing_root_fails(self):
        report = verify_site(self.root / "nope")
        self.assertFalse(report.ok)

    def test_slug_from_path(self):
        self.assertEqual(slug_from_path("project/alpha-1/"), "alpha-1")
        self.assertIsNone(slug_from_path("project/alpha-1"))
        self.assertIsNone(slug_from_path("/project/alpha-1/"))
        self.assertIsNone(slug_from_path("elsewhere/alpha-1/"))


class MissingPageTests(VerifySiteTestCase):
    def test_missing_page_breaks_parity(self):
        # gamma's page vanishes; meta, index, sitemap and records all still cite it.
        page = self.root / "project" / "acme-gamma-3" / "index.html"
        page.unlink()
        report = self.assertFailsWith(
            "catalog-meta.json total_projects=3 but 2 project pages exist",
            "data/projects/acme-gamma-3.json has no generated page",
        )
        self.assertEqual(report.counts["pages on disk"], 2)

    def test_missing_page_dangles_incoming_related_links(self):
        (self.root / "project" / "acme-gamma-3" / "index.html").unlink()
        self.assertFailsWith("../../project/acme-gamma-3/ which does not exist")


class DuplicateSlugTests(VerifySiteTestCase):
    def test_duplicate_path_in_index_is_reported(self):
        entries = self.read_json("data/index.json")
        entries[1]["path"] = entries[0]["path"]
        self.write_json("data/index.json", entries)
        self.assertFailsWith(
            "is duplicated",
            "slug collision",
        )


class DanglingRelatedLinkTests(VerifySiteTestCase):
    def test_dangling_related_link_is_named(self):
        page = self.root / "project" / "acme-alpha-1" / "index.html"
        page.write_text(
            page.read_text(encoding="utf-8").replace(
                'href="../../project/acme-beta-2/"',
                'href="../../project/acme-ghost-99/"',
            ),
            encoding="utf-8",
        )
        self.assertFailsWith(
            "project/acme-alpha-1/index.html links to ../../project/acme-ghost-99/ "
            "which does not exist"
        )


class HomepageIndexTests(VerifySiteTestCase):
    def test_missing_index_json(self):
        (self.root / "data" / "index.json").unlink()
        self.assertFailsWith("data/index.json is missing")

    def test_malformed_index_json(self):
        (self.root / "data" / "index.json").write_text("[{oops", encoding="utf-8")
        self.assertFailsWith("data/index.json is not valid JSON")

    def test_index_json_wrong_shape(self):
        self.write_json("data/index.json", {"projects": []})
        self.assertFailsWith("data/index.json must be a JSON array")

    def test_index_entry_count_mismatch(self):
        entries = self.read_json("data/index.json")
        self.write_json("data/index.json", entries[:-1])
        self.assertFailsWith("data/index.json has 2 entries but 3 project pages")

    def test_index_entry_path_does_not_resolve(self):
        entries = self.read_json("data/index.json")
        entries[0]["path"] = "project/does-not-exist-42/"
        self.write_json("data/index.json", entries)
        self.assertFailsWith(
            "'project/does-not-exist-42/' does not resolve to a generated page"
        )

    def test_index_entry_missing_path(self):
        entries = self.read_json("data/index.json")
        del entries[0]["path"]
        self.write_json("data/index.json", entries)
        self.assertFailsWith("has no 'path'")

    def test_index_entry_malformed_path(self):
        entries = self.read_json("data/index.json")
        entries[0]["path"] = "/project/acme-alpha-1"
        self.write_json("data/index.json", entries)
        self.assertFailsWith("malformed path")


class CatalogMetaTests(VerifySiteTestCase):
    def test_missing_catalog_meta(self):
        (self.root / "data" / "catalog-meta.json").unlink()
        self.assertFailsWith("data/catalog-meta.json is missing")

    def test_total_projects_mismatch(self):
        meta = self.read_json("data/catalog-meta.json")
        meta["total_projects"] = 999
        self.write_json("data/catalog-meta.json", meta)
        self.assertFailsWith("total_projects=999 but 3 project pages exist")

    def test_malformed_catalog_meta(self):
        (self.root / "data" / "catalog-meta.json").write_text("{", encoding="utf-8")
        self.assertFailsWith("data/catalog-meta.json is not valid JSON")


class SitemapTests(VerifySiteTestCase):
    def test_missing_sitemap(self):
        (self.root / "sitemap.xml").unlink()
        self.assertFailsWith("sitemap.xml is missing")

    def test_malformed_sitemap_xml(self):
        (self.root / "sitemap.xml").write_text("<urlset><url>", encoding="utf-8")
        self.assertFailsWith("sitemap.xml is not well-formed XML")

    def test_sitemap_count_mismatch(self):
        # Drop one <url> block: 3 locs remain where 4 (3 pages + homepage) are due.
        text = (self.root / "sitemap.xml").read_text(encoding="utf-8")
        lines = [line for line in text.splitlines(True) if "acme-gamma-3" not in line]
        (self.root / "sitemap.xml").write_text("".join(lines), encoding="utf-8")
        self.assertFailsWith("sitemap.xml has 3 <loc> entries but expected 4")

    def test_sitemap_loc_does_not_resolve(self):
        text = (self.root / "sitemap.xml").read_text(encoding="utf-8")
        (self.root / "sitemap.xml").write_text(
            text.replace("acme-gamma-3", "acme-phantom-77"), encoding="utf-8"
        )
        self.assertFailsWith(
            "sitemap.xml <loc> https://example.com/project/acme-phantom-77/ "
            "does not resolve to a generated page"
        )

    def test_sitemap_missing_homepage(self):
        text = (self.root / "sitemap.xml").read_text(encoding="utf-8")
        lines = [
            line
            for line in text.splitlines(True)
            if "<loc>https://example.com/</loc>" not in line
        ]
        (self.root / "sitemap.xml").write_text("".join(lines), encoding="utf-8")
        self.assertFailsWith("sitemap.xml does not list the homepage")


class SitemapWithoutSiteUrlTests(VerifySiteTestCase):
    """No SITE_URL configured: the generator omits absolute locs on purpose."""

    site_url = None

    def test_empty_sitemap_is_valid_without_site_url(self):
        report = self.assertPasses()
        self.assertEqual(report.counts["sitemap locs"], 0)


class MissingAssetTests(VerifySiteTestCase):
    def test_each_missing_asset_is_named(self):
        for name in REQUIRED_ASSETS:
            with self.subTest(asset=name):
                (self.root / name).unlink()
                self.assertFailsWith(f"required asset missing from output: {name}")
                (self.root / name).write_text("restored", encoding="utf-8")
        self.assertPasses()


class MissingRecordTests(VerifySiteTestCase):
    def test_missing_project_record(self):
        (self.root / "data" / "projects" / "acme-beta-2.json").unlink()
        self.assertFailsWith(
            "page project/acme-beta-2/ has no data/projects/acme-beta-2.json record"
        )

    def test_missing_projects_directory(self):
        for path in (self.root / "data" / "projects").glob("*.json"):
            path.unlink()
        (self.root / "data" / "projects").rmdir()
        self.assertFailsWith("data/projects/ directory is missing")


if __name__ == "__main__":
    unittest.main()
