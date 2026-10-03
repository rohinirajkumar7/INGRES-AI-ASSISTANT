"""HTTP-level tests. Skipped automatically if FastAPI isn't installed."""
import unittest

from tests import helpers  # noqa: F401

try:
    from fastapi.testclient import TestClient
    from ingres.app import app
    HAVE_FASTAPI = True
except Exception:  # pragma: no cover
    HAVE_FASTAPI = False


@unittest.skipUnless(HAVE_FASTAPI, "fastapi not installed")
class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health(self):
        body = self.client.get("/api/health").json()
        self.assertEqual(body["status"], "healthy")
        self.assertEqual(body["rows"], 726)
        self.assertFalse(body["gemini_configured"])

    def test_stats_total_not_shadowed_by_state_route(self):
        # regression: /stats/{state} used to capture /stats/total and 404
        r = self.client.get("/api/stats/total")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["total_states"], 37)
        self.assertEqual(self.client.get("/api/stats/Punjab").json()["state"], "Punjab")

    def test_routes_work_with_and_without_api_prefix(self):
        self.assertEqual(self.client.get("/states").status_code, 200)
        self.assertEqual(len(self.client.get("/api/states").json()), 37)

    def test_unknown_state_is_404(self):
        self.assertEqual(self.client.get("/api/districts/Narnia").status_code, 404)
        self.assertEqual(self.client.get("/api/stats/Narnia").status_code, 404)

    def test_chat_ok_and_validation(self):
        r = self.client.post("/api/chat", json={"message": "rainfall in Delhi", "language": "en"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("Delhi", r.json()["response"])
        self.assertEqual(self.client.post("/api/chat", json={"message": ""}).status_code, 422)
        self.assertEqual(self.client.post("/api/chat", json={"message": "x" * 501}).status_code, 422)
        self.assertEqual(self.client.post("/api/chat", json={}).status_code, 422)

    def test_chat_context_roundtrip(self):
        first = self.client.post("/api/chat", json={"message": "Punjab"}).json()
        second = self.client.post("/api/chat", json={"message": "and its recharge", "context": first["context"]}).json()
        self.assertTrue(second["response"].startswith("Punjab"))

    def test_map_and_rankings(self):
        tiles = self.client.get("/api/map").json()["tiles"]
        self.assertEqual(len(tiles), 37)
        r = self.client.get("/api/rankings", params={"metric": "extraction", "limit": 3}).json()
        self.assertEqual(len(r["items"]), 3)
        self.assertEqual(self.client.get("/api/rankings", params={"metric": "nope"}).status_code, 422)
        self.assertEqual(self.client.get("/api/rankings", params={"order": "sideways"}).status_code, 422)


if __name__ == "__main__":
    unittest.main()
