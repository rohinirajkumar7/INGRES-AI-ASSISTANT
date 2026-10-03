import unittest

from tests import helpers  # noqa: F401
from ingres.data import get_store
from ingres.locations import LocationIndex
from ingres.nlu import detect_language, rule_parse, sanitize


class SanitizeTests(unittest.TestCase):
    def test_clamps_bad_model_output(self):
        out = sanitize({"intent": "drop table", "metric": "x", "limit": 999, "language": "xx",
                        "locations": ["a" * 200, "b", "c", "d", "e", "f"], "category": "weird"})
        self.assertEqual(out["intent"], "unknown")
        self.assertEqual(out["metric"], "overview")
        self.assertEqual(out["limit"], 10)
        self.assertEqual(out["language"], "en")
        self.assertEqual(len(out["locations"]), 4)
        self.assertLessEqual(len(out["locations"][0]), 60)
        self.assertIsNone(out["category"])

    def test_non_dict_is_safe(self):
        self.assertEqual(sanitize("nope")["intent"], "unknown")


class RuleParseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ix = LocationIndex(get_store())

    def parse(self, text):
        return rule_parse(text, self.ix)

    def test_greeting_bug_fixed(self):
        # old code matched 'hi' inside 'Delhi'
        self.assertEqual(self.parse("hi")["intent"], "greet")
        r = self.parse("rainfall in Delhi")
        self.assertEqual(r["intent"], "lookup")
        self.assertEqual(r["metric"], "rainfall")
        self.assertEqual(r["locations"], ["Delhi"])

    def test_compare(self):
        r = self.parse("Compare Karnataka and Kerala")
        self.assertEqual((r["intent"], r["locations"]), ("compare", ["Karnataka", "Kerala"]))
        self.assertEqual(self.parse("Punjab vs Haryana")["intent"], "compare")

    def test_ranking_variants(self):
        r = self.parse("top 3 over-exploited districts in Punjab")
        self.assertEqual((r["intent"], r["limit"], r["category"]), ("ranking", 3, "over_exploited"))
        r = self.parse("which states have lowest rainfall")
        self.assertEqual((r["intent"], r["level"], r["order"], r["metric"]), ("ranking", "state", "asc", "rainfall"))

    def test_categories_and_list(self):
        self.assertEqual(self.parse("how many districts are critical in Gujarat")["intent"], "categories")
        self.assertEqual(self.parse("show all states")["intent"], "list_states")

    def test_unknown_place_is_kept_for_error_message(self):
        r = self.parse("rainfall in Atlantis")
        self.assertEqual(r["locations"], ["atlantis"])

    def test_language_detection(self):
        self.assertEqual(detect_language("ಮಳೆ ಎಷ್ಟು"), "kn")
        self.assertEqual(detect_language("மழை"), "ta")
        self.assertEqual(detect_language("వర్షం"), "te")
        self.assertEqual(detect_language("বৃষ্টি"), "bn")
        self.assertEqual(detect_language("વરસાદ"), "gu")
        self.assertEqual(detect_language("बारिश"), "hi")
        self.assertEqual(detect_language("पाऊस किती आहे"), "mr")
        self.assertEqual(detect_language("rain"), "en")

    def test_hindi_keyword_with_english_place(self):
        r = self.parse("वर्षा Delhi")
        self.assertEqual((r["intent"], r["metric"], r["language"]), ("lookup", "rainfall", "hi"))

    def test_metric_only_follow_up_leaves_place_empty(self):
        # "and its recharge" must not hard-code India, or context is never reused
        r = self.parse("and its recharge")
        self.assertEqual((r["intent"], r["metric"], r["locations"]), ("lookup", "recharge", []))

    def test_explicit_india_is_kept(self):
        self.assertEqual(self.parse("recharge in India")["locations"], ["India"])


if __name__ == "__main__":
    unittest.main()
