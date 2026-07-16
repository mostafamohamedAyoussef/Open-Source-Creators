import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.processor import (
    COMMERCIAL_MAPPING,
    NON_TOOL_SCORE_CAP,
    _keyword_regex,
    is_curated_list,
    is_non_tool,
    map_commercial_alternative,
    process_repos,
)


def repo(description=None, topics=None):
    return {"description": description, "topics": topics or []}


class KeywordRegexTest(unittest.TestCase):
    def test_dotted_keyword_dot_is_literal_not_wildcard(self):
        rx = _keyword_regex("copy.ai")
        self.assertTrue(rx.search("built on copy.ai today"))
        self.assertIsNone(rx.search("built on copyxai today"))

    def test_multi_word_keyword_tolerates_whitespace_runs(self):
        rx = _keyword_regex("adobe audition")
        self.assertTrue(rx.search("an adobe audition clone"))
        self.assertTrue(rx.search("an adobe   audition clone"))
        self.assertTrue(rx.search("an adobe\naudition clone"))
        self.assertIsNone(rx.search("adobe premiere and audition"))

    def test_hyphenated_keyword_matches_literal_form(self):
        rx = _keyword_regex("text-to-image")
        self.assertTrue(rx.search("a text-to-image model"))
        self.assertTrue(rx.search("text-to-image, fast"))
        # A hyphen is a boundary, so compound tags still match legitimately.
        self.assertTrue(rx.search("a text-to-image-generation pipeline"))
        # ...but the keyword must not be swallowed by a longer word.
        self.assertIsNone(rx.search("a text-to-imagex model"))
        self.assertIsNone(rx.search("atext-to-image model"))

    def test_regexes_are_compiled_once_per_keyword(self):
        self.assertIs(_keyword_regex("midjourney"), _keyword_regex("midjourney"))

    def test_short_keyword_needs_word_boundaries(self):
        rx = _keyword_regex("rag")
        for good in ("a rag pipeline", "rag-based agent", "uses RAG.".lower(), "(rag)"):
            self.assertTrue(rx.search(good), good)
        for bad in ("object storage layer", "dragging the mouse", "a fragment", "ragged"):
            self.assertIsNone(rx.search(bad), bad)

    def test_non_ascii_prose_counts_as_a_boundary(self):
        # re's \b would fail here: CJK chars are word chars, so there is no
        # boundary between "持" and "C". This must still match.
        self.assertTrue(_keyword_regex("chatgpt").search("支持chatgpt多轮对话"))


class MapCommercialAlternativeTest(unittest.TestCase):
    def test_substring_false_positives_are_gone(self):
        # Real regressions observed in data/processed_repos.json.
        self.assertNotIn("Canva", map_commercial_alternative(
            repo("Infinite canvas drawing/whiteboarding app")))
        self.assertNotIn("Descript", map_commercial_alternative(
            repo("Personalized Product Description Generation in E-commerce")))
        self.assertNotIn("ElevenLabs", map_commercial_alternative(
            repo("TTSR: Learning Texture Transformer Network for Super-Resolution")))
        self.assertNotIn("Midjourney", map_commercial_alternative(
            repo("Fluxos de automacao para agentes via LLM")))

    def test_legitimate_description_matches_are_kept(self):
        self.assertIn("Canva", map_commercial_alternative(
            repo("Open source alternative to Canva AI")))
        self.assertIn("ElevenLabs", map_commercial_alternative(
            repo("MARS5 speech model (TTS) from CAMB.AI")))
        self.assertIn("Midjourney", map_commercial_alternative(
            repo("FLUX, Stable Diffusion and SDXL fine tuning")))
        self.assertIn("Adobe Premiere", map_commercial_alternative(
            repo("MCP server for Adobe Premiere Pro")))

    def test_description_matching_is_case_insensitive(self):
        self.assertIn("Midjourney", map_commercial_alternative(repo("A MidJourney clone")))
        self.assertIn("ElevenLabs", map_commercial_alternative(repo("Realtime TTS engine")))

    def test_topics_match_exactly_not_by_substring(self):
        self.assertIn("Canva", map_commercial_alternative(repo(None, ["canva"])))
        # An exact-membership check must not fire on a longer, unrelated tag.
        self.assertNotIn("Canva", map_commercial_alternative(repo(None, ["canvas"])))
        self.assertNotIn("Notion", map_commercial_alternative(repo(None, ["notion-api-clone"])))

    def test_topic_match_wins_even_when_description_is_silent(self):
        self.assertEqual(
            ["Figma"], map_commercial_alternative(repo("A tool for teams", ["penpot"])))

    def test_missing_and_null_fields_are_safe(self):
        self.assertEqual([], map_commercial_alternative({}))
        self.assertEqual([], map_commercial_alternative(repo(None, [])))
        self.assertEqual([], map_commercial_alternative(repo("nothing relevant here")))

    def test_multiple_alternatives_and_order_follows_mapping(self):
        result = map_commercial_alternative(repo("AI video-editing suite", ["copywriting"]))
        self.assertEqual(["Adobe Premiere", "CapCut", "Jasper", "Copy.ai", "Descript"], result)

    def test_every_configured_keyword_matches_itself(self):
        # Guards against a keyword whose escaping or boundaries make it unmatchable.
        for commercial, keywords in COMMERCIAL_MAPPING.items():
            for kw in keywords:
                with self.subTest(commercial=commercial, keyword=kw):
                    self.assertIn(commercial, map_commercial_alternative(repo(f"a {kw} thing")))
                    self.assertIn(commercial, map_commercial_alternative(repo(None, [kw])))

    def test_custom_mapping_is_honoured(self):
        with patch.dict(COMMERCIAL_MAPPING, {"Fake": ["seo"]}, clear=True):
            self.assertEqual(["Fake"], map_commercial_alternative(repo("seo audit tool")))
            self.assertEqual([], map_commercial_alternative(repo("a seoul travel guide")))


class CuratedListDetectionTest(unittest.TestCase):
    """A list about tools must not outrank the tools it links to."""

    @staticmethod
    def r(name="thing", description=None, topics=()):
        return {"name": name, "description": description, "topics": list(topics)}

    def test_awesome_naming_convention_is_a_list(self):
        self.assertTrue(is_curated_list(self.r("awesome-creative-coding")))
        self.assertTrue(is_curated_list(self.r("awesome")))

    def test_awesome_prefix_is_not_vetoed_by_tool_topics(self):
        # The naming convention is definitive: an awesome-* repo stays a list even
        # if it also carries software topics.
        self.assertTrue(is_curated_list(self.r("awesome-n8n-templates", topics=["automation"])))

    def test_substring_awesome_is_not_a_list(self):
        # "awesomeness-tracker" is not an awesome-* list; the hyphen matters.
        self.assertFalse(is_curated_list(self.r("awesomeness-tracker")))

    def test_self_declared_list_topics(self):
        # joshbuchea/HEAD: tagged "list", ranked 10.0 inside Marketing Automation.
        self.assertTrue(is_curated_list(self.r("HEAD", "everything for the <head>", ["list", "seo"])))
        self.assertTrue(is_curated_list(self.r("x", topics=["awesome-list"])))
        self.assertTrue(is_curated_list(self.r("x", topics=["resources"])))

    def test_curation_phrase_in_description(self):
        self.assertTrue(is_curated_list(self.r("x", "A curated list of design tools")))
        self.assertTrue(is_curated_list(self.r("x", "Curated collection of prompts")))
        self.assertTrue(is_curated_list(self.r("x", "A list of awesome video editors")))

    def test_tool_topics_veto_a_subject_tag(self):
        # backlink-pilot is a Playwright CLI tagged "awesome-lists" because it SUBMITS
        # products TO awesome-lists. The tag names its subject, not its nature.
        self.assertFalse(is_curated_list(self.r(
            "backlink-pilot",
            "Automated backlink submission toolkit - submit your product to awesome-lists",
            ["awesome-lists", "automation", "playwright"],
        )))

    def test_tool_whose_description_merely_says_list(self):
        # Matalogue is a real Blender addon: "List of node trees to switch between".
        self.assertFalse(is_curated_list(self.r("Matalogue", "List of node trees to switch between quickly")))
        self.assertFalse(is_curated_list(self.r("x", "Generate a list of hashtags for your post")))

    def test_missing_description_does_not_crash(self):
        self.assertFalse(is_curated_list(self.r("x", None)))

    def test_career_material_is_not_a_creator_tool(self):
        # hiring-without-whiteboards is tagged "whiteboard" (as in whiteboard
        # interviews) and so was collected into Design Tools at a perfect 10.0.
        self.assertTrue(is_non_tool(self.r("hiring-without-whiteboards", topics=["hiring", "whiteboard"])))
        self.assertFalse(is_non_tool(self.r("excalidraw", topics=["whiteboard", "canvas"])))


class NonToolScoringTest(unittest.TestCase):
    """The cap must apply through process_repos, not just in isolation."""

    def _process(self, records):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir()
            (root / "data" / "raw_repos.json").write_text(json.dumps(records), encoding="utf-8")
            with patch("scripts.site_generator.build_site", return_value={"total_projects": 0}):
                process_repos(root)
            return json.loads((root / "data" / "processed_repos.json").read_text(encoding="utf-8"))

    @staticmethod
    def _raw(name, topics, stars=50000):
        return {
            "id": abs(hash(name)) % 10**6, "name": name, "full_name": f"o/{name}",
            "description": "A tool for making things", "stargazers_count": stars,
            "topics": list(topics), "categories": ["Design Tools"],
            "updated_at": "2026-07-10T00:00:00Z", "created_at": "2020-01-01T00:00:00Z",
        }

    def test_list_is_capped_and_tagged_while_tool_is_untouched(self):
        out = self._process([
            self._raw("awesome-design", ["design"]),
            self._raw("realtool", ["design"]),
        ])
        by = {r["name"]: r for r in out}

        self.assertLessEqual(by["awesome-design"]["score"], NON_TOOL_SCORE_CAP)
        self.assertTrue(by["awesome-design"]["is_curated_list"])
        self.assertIn("list", by["awesome-design"]["tags"])

        # The real tool keeps its full score and is not tagged as a list.
        self.assertGreater(by["realtool"]["score"], NON_TOOL_SCORE_CAP)
        self.assertFalse(by["realtool"]["is_curated_list"])
        self.assertNotIn("list", by["realtool"]["tags"])

    def test_list_cannot_claim_to_replace_a_product(self):
        # A list of Midjourney prompts does not replace Midjourney.
        raw = self._raw("awesome-midjourney-prompts", ["text-to-image"])
        out = self._process([raw])
        self.assertEqual([], out[0]["commercial_alternatives"])

    def test_capped_list_is_never_a_hidden_gem(self):
        out = self._process([self._raw("awesome-gems", ["design"], stars=900)])
        self.assertFalse(out[0]["is_hidden_gem"])


if __name__ == "__main__":
    unittest.main()
