import unittest
from unittest.mock import patch

from scripts.processor import COMMERCIAL_MAPPING, _keyword_regex, map_commercial_alternative


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


if __name__ == "__main__":
    unittest.main()
