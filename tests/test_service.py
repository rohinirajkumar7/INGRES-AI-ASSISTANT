import unittest

from tests import helpers
from tests.helpers import FakeLLM, run
from ingres.service import ChatService, NotFound


class OfflineChatTests(unittest.TestCase):
    """No LLM at all: the rule-based path must still answer well."""

    @classmethod
    def setUpClass(cls):
        cls.svc = ChatService(llm=None)

    def chat(self, text, **kw):
        return run(self.svc.chat(text, **kw))

    def test_greeting_and_help(self):
        self.assertIn("INGRES", self.chat("hello")["response"])
        self.assertIn("compare", self.chat("what can you do")["response"].lower())

    def test_state_lookup_has_charts_and_context(self):
        r = self.chat("Karnataka")
        self.assertEqual(r["source"], "rules")
        self.assertEqual(r["context"], {"state": "Karnataka"})
        self.assertEqual([c["type"] for c in r["charts"]], ["categories", "bar"])
        self.assertIn("31 districts", r["response"])

    def test_district_lookup_via_alias(self):
        r = self.chat("rainfall in Bangalore")
        self.assertTrue(r["response"].startswith("Bengaluru (Urban) (Karnataka): average rainfall"))
        self.assertEqual(r["data"][0]["name"], "Bengaluru (Urban)")

    def test_compare(self):
        r = self.chat("compare Punjab and Kerala")
        self.assertEqual(len(r["data"]), 2)
        self.assertEqual(r["charts"][0]["type"], "comparison")
        self.assertIn("Highest extraction pressure: Punjab", r["response"])

    def test_compare_with_one_place_falls_back_to_lookup(self):
        self.assertTrue(self.chat("compare Punjab")["response"].startswith("Punjab:"))

    def test_ranking_matches_store(self):
        r = self.chat("top 3 over-exploited districts in Punjab")
        self.assertEqual(len(r["charts"][0]["data"]), 3)
        values = [d["value"] for d in r["charts"][0]["data"]]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_state_ranking_has_map(self):
        r = self.chat("which states have lowest rainfall")
        self.assertEqual([c["type"] for c in r["charts"]], ["bar", "map"])
        self.assertTrue(r["response"].splitlines()[1].startswith("1. Ladakh"))

    def test_categories(self):
        r = self.chat("how many districts are over exploited in Rajasthan")
        self.assertIn("27 of 33", r["response"])

    def test_list_states_and_india(self):
        self.assertEqual(self.chat("show all states")["charts"][0]["type"], "map")
        self.assertIn("India overall", self.chat("india")["response"])

    def test_follow_up_uses_context(self):
        r = self.chat("what about its recharge", context={"state": "Punjab"})
        self.assertTrue(r["response"].startswith("Punjab: annual recharge"))

    def test_unknown_place_and_gibberish(self):
        self.assertIn("couldn't find", self.chat("rainfall in Atlantis")["response"])
        self.assertIn("didn't understand", self.chat("asdfgh")["response"])

    def test_non_english_without_key_gets_notice(self):
        r = self.chat("वर्षा Delhi", language="hi")
        self.assertIn("GEMINI_API_KEY", r["notice"])

    def test_read_api(self):
        self.assertEqual(len(self.svc.states()), 37)
        self.assertIn("Sangrur", self.svc.districts("punjab"))
        self.assertEqual(self.svc.state_stats("tamilnadu")["state"], "Tamil Nadu")
        with self.assertRaises(NotFound):
            self.svc.districts("Narnia")
        top = self.svc.rankings("extraction", "desc", 3, level="state")
        self.assertEqual(top["items"][0]["name"], "Punjab")
        with self.assertRaises(ValueError):
            self.svc.rankings("bogus")


class WithLLMTests(unittest.TestCase):
    def test_llm_result_is_used_and_localized(self):
        llm = FakeLLM({"intent": "lookup", "metric": "rainfall", "locations": ["Pune"], "language": "hi"})
        r = run(ChatService(llm=llm).chat("पुणे में बारिश", language="auto"))
        self.assertEqual(r["source"], "gemini")
        self.assertEqual(r["language"], "hi")
        self.assertTrue(r["response"].startswith("[hi] Pune (Maharashtra)"))
        self.assertIsNone(r["notice"])

    def test_compare_needs_two_places(self):
        llm = FakeLLM({"intent": "compare", "locations": ["Punjab"]})
        r = run(ChatService(llm=llm).chat("compare punjab", language="en"))
        self.assertIn("at least two", r["response"])

    def test_english_makes_single_llm_call(self):
        llm = FakeLLM({"intent": "greet"})
        run(ChatService(llm=llm).chat("hello", language="en"))
        self.assertEqual([c[0] for c in llm.calls], ["parse"])

    def test_llm_failure_falls_back_to_rules(self):
        llm = FakeLLM(fail_parse=True)
        r = run(ChatService(llm=llm).chat("rainfall in Delhi", language="en"))
        self.assertEqual(r["source"], "rules")
        self.assertIn("Delhi", r["response"])

    def test_localization_failure_keeps_english_with_notice(self):
        llm = FakeLLM({"intent": "greet", "language": "ta"}, fail_localize=True)
        r = run(ChatService(llm=llm).chat("வணக்கம்", language="ta"))
        self.assertIn("English", r["notice"])
        self.assertIn("INGRES", r["response"])

    def test_rules_rescue_unknown_model_output(self):
        llm = FakeLLM({"intent": "unknown"})
        r = run(ChatService(llm=llm).chat("compare Punjab and Haryana", language="en"))
        self.assertEqual(r["charts"][0]["type"], "comparison")

    def test_model_garbage_cannot_break_routing(self):
        llm = FakeLLM({"intent": "ranking", "metric": "???", "limit": "lots", "level": 5, "locations": [None]})
        r = run(ChatService(llm=llm).chat("anything", language="en"))
        self.assertTrue(r["response"])

    def test_ambiguous_district_resolved_with_state_from_llm(self):
        llm = FakeLLM({"intent": "lookup", "locations": ["Aurangabad", "Maharashtra"]})
        r = run(ChatService(llm=llm).chat("Aurangabad Maharashtra", language="en"))
        self.assertIn("Aurangabad (Maharashtra)", r["response"])


if __name__ == "__main__":
    unittest.main()
