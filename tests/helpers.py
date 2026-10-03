import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["GEMINI_API_KEY"] = ""
os.environ["GOOGLE_API_KEY"] = ""


def run(coro):
    return asyncio.run(coro)


class FakeLLM:
    """Stands in for GeminiClient in tests."""

    def __init__(self, nlu=None, fail_parse=False, fail_localize=False, configured=True):
        self.nlu = nlu or {}
        self.fail_parse = fail_parse
        self.fail_localize = fail_localize
        self.configured = configured
        self.available = configured
        self.last_error = None
        self.models = ["fake"]
        self.calls = []

    async def parse(self, message, context=None):
        self.calls.append(("parse", message))
        if self.fail_parse:
            raise RuntimeError("boom")
        from ingres.nlu import sanitize
        return sanitize(self.nlu)

    async def localize(self, text, language):
        self.calls.append(("localize", language))
        if self.fail_localize:
            raise RuntimeError("boom")
        return f"[{language}] {text}"
