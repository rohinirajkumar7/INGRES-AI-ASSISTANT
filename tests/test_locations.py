import unittest

from tests import helpers  # noqa: F401
from ingres.data import get_store
from ingres.locations import LocationIndex


class LocationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ix = LocationIndex(get_store())

    def one(self, text):
        found = self.ix.find_all(text)
        self.assertTrue(found, f"nothing found in {text!r}")
        return found[0]

    def test_aliases(self):
        self.assertEqual(self.one("Bangalore").district, "Bengaluru (Urban)")
        self.assertEqual(self.one("mysore").district, "Mysuru")
        self.assertEqual(self.one("bombay").district, "Mumbai")
        self.assertEqual(self.one("tamilnadu").state, "Tamil Nadu")
        self.assertEqual(self.one("Orissa").state, "Odisha")

    def test_typo_tolerance(self):
        self.assertEqual(self.one("Banglore").district, "Bengaluru (Urban)")
        self.assertEqual(self.one("chenai").district, "Chennai")

    def test_state_wins_over_same_name_district(self):
        self.assertEqual(self.one("delhi").kind, "state")
        self.assertEqual(self.one("puducherry").kind, "state")

    def test_ambiguous_district_uses_state_hint(self):
        both = self.ix.find_all("Aurangabad Maharashtra")
        self.assertEqual(both[0].state, "Maharashtra")
        self.assertTrue(self.one("Aurangabad").also_in)

    def test_generic_words_are_not_places(self):
        self.assertEqual(self.ix.find_all("north central data south"), [])

    def test_query_words_not_fuzzy_matched(self):
        self.assertEqual(self.ix.find_all("show rainfall and extraction"), [])

    def test_resolve_for_llm_names(self):
        self.assertEqual(self.ix.resolve("Karnataka").state, "Karnataka")
        self.assertEqual(self.ix.resolve("Bengaluru").district, "Bengaluru (Urban)")
        self.assertIsNone(self.ix.resolve("zzzzzzzz"))


if __name__ == "__main__":
    unittest.main()
