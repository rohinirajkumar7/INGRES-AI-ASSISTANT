import os
import time
import unittest

from tests import helpers
from tests.helpers import run
from ingres.gemini import GeminiClient, LLMError


class GeminiClientTests(unittest.TestCase):
    def setUp(self):
        self._old = {k: os.environ.get(k) for k in ("GEMINI_API_KEY", "GEMINI_MODEL")}

    def tearDown(self):
        for k, v in self._old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_placeholder_or_empty_key_means_not_configured(self):
        for value in ("", "your-gemini-api-key-here"):
            os.environ["GEMINI_API_KEY"] = value
            self.assertFalse(GeminiClient().configured)

    def test_real_looking_key_is_configured(self):
        os.environ["GEMINI_API_KEY"] = "AIza-test"
        self.assertTrue(GeminiClient().configured)

    def test_models_come_from_env(self):
        os.environ["GEMINI_MODEL"] = "my-model"
        self.assertEqual(GeminiClient().models[0], "my-model")

    def test_parse_handles_fenced_json_and_sanitizes(self):
        client = GeminiClient()

        async def fake(system, prompt, json_mode, max_tokens):
            return '```json\n{"intent": "lookup", "metric": "rainfall", "locations": ["Pune"], "limit": 99}\n```'
        client._generate = fake
        out = run(client.parse("rain in pune"))
        self.assertEqual((out["intent"], out["metric"], out["locations"], out["limit"]),
                         ("lookup", "rainfall", ["Pune"], 10))

    def test_parse_rejects_non_json(self):
        client = GeminiClient()

        async def fake(*a, **k):
            return "I am sorry, I cannot"
        client._generate = fake
        with self.assertRaises(LLMError):
            run(client.parse("hello"))

    def test_parse_is_cached(self):
        client = GeminiClient()
        calls = []

        async def fake(*a, **k):
            calls.append(1)
            return '{"intent": "greet"}'
        client._generate = fake
        run(client.parse("Hello"))
        run(client.parse("hello"))
        self.assertEqual(len(calls), 1)

    def test_cooldown_blocks_availability(self):
        os.environ["GEMINI_API_KEY"] = "AIza-test"
        client = GeminiClient()
        self.assertTrue(client.available)
        client._cooldown_until = time.time() + 60
        self.assertFalse(client.available)

    def test_localize_english_is_noop(self):
        self.assertEqual(run(GeminiClient().localize("hello", "en")), "hello")


if __name__ == "__main__":
    unittest.main()
