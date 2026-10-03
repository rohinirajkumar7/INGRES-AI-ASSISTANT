import unittest

from tests import helpers  # noqa: F401  (sets sys.path / env)
from ingres.data import category_for, display_name, get_store
from ingres.geo import TILES, map_tiles


class DataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = get_store()

    def test_loads_expected_shape(self):
        self.assertEqual(len(self.store.districts), 726)
        self.assertEqual(len(self.store.states), 37)
        self.assertTrue(all(self.store.districts_of(s) for s in self.store.states))

    def test_uses_total_columns_not_first_subcolumn(self):
        # regression: old loader read the 'C' sub-column and got wrong/zero values
        chennai = self.store.find_district("Tamil Nadu", "Chennai")
        self.assertAlmostEqual(chennai.rainfall, 1453.24, places=1)
        self.assertAlmostEqual(chennai.stage, 121.72, places=1)

    def test_category_boundaries(self):
        self.assertEqual(category_for(None), "no_data")
        self.assertEqual(category_for(70), "safe")
        self.assertEqual(category_for(70.01), "semi_critical")
        self.assertEqual(category_for(90), "semi_critical")
        self.assertEqual(category_for(100), "critical")
        self.assertEqual(category_for(100.01), "over_exploited")

    def test_state_stage_is_weighted_not_mean(self):
        agg = self.store.state_summary("Punjab")
        districts = self.store.districts_of("Punjab")
        expected = sum(d.extraction for d in districts) / sum(d.extractable for d in districts) * 100
        self.assertAlmostEqual(agg["stage"], expected, delta=0.01)
        self.assertEqual(agg["category"], "over_exploited")

    def test_india_summary_counts_add_up(self):
        agg = self.store.india_summary()
        self.assertEqual(sum(agg["counts"].values()), agg["n_districts"])
        self.assertTrue(50 < agg["stage"] < 70)

    def test_display_names(self):
        self.assertEqual(display_name("TAMILNADU"), "Tamil Nadu")
        self.assertEqual(display_name("ANDAMAN AND NICOBAR ISLANDS"), "Andaman and Nicobar Islands")

    def test_ranking_sorted_and_filtered(self):
        total, items = self.store.rank_districts("extraction", "desc", 5, "Punjab", "over_exploited")
        stages = [d.stage for d in items]
        self.assertEqual(stages, sorted(stages, reverse=True))
        self.assertTrue(all(d.category == "over_exploited" and d.state == "Punjab" for d in items))
        self.assertGreaterEqual(total, len(items))

    def test_every_state_has_unique_map_tile(self):
        self.assertEqual(set(self.store.states) - set(TILES), set())
        positions = [(r, c) for _, r, c in TILES.values()]
        self.assertEqual(len(positions), len(set(positions)))
        self.assertEqual(len(map_tiles(self.store)), 37)


if __name__ == "__main__":
    unittest.main()
