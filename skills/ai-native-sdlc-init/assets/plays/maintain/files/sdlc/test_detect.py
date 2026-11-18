import os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from detect import detect  # noqa: E402

STEADY = [10.0, 11.0, 9.0, 10.0] * 6  # mean 10, sigma ~0.707


class Detect(unittest.TestCase):
    def tier(self, recent, **kw):
        return detect(STEADY + recent, **kw)["tier"]

    def test_within_band(self):
        self.assertEqual(self.tier([10, 9, 10, 11, 10, 9, 10, 10]), "none")

    def test_tiers_from_latest(self):
        self.assertEqual(self.tier([10, 9, 10, 11, 10, 9, 10, 10.8]), "1sigma")
        self.assertEqual(self.tier([10, 9, 10, 11, 10, 9, 10, 11.5]), "2sigma")
        self.assertEqual(self.tier([10, 9, 10, 11, 10, 9, 10, 13]), "3sigma")

    def test_direction_down(self):
        self.assertEqual(self.tier([10, 9, 10, 11, 10, 9, 10, 7], direction="down"), "3sigma")
        self.assertEqual(self.tier([10, 9, 10, 11, 10, 9, 10, 13], direction="down"), "none")

    def test_drift_four_of_five(self):
        r = detect(STEADY + [10, 10, 10, 10.8, 10.8, 10, 10.8, 10.8])
        self.assertEqual((r["tier"], r["rule"]), ("2sigma", "drift: 4 of last 5 beyond 1 sigma"))

    def test_drift_eight_above_mean(self):
        r = detect(STEADY + [10.2] * 8)
        self.assertEqual(r["tier"], "2sigma")
        self.assertIn("in a row", r["rule"])

    def test_sigma_floor_on_flat_baseline(self):
        flat = [0.0] * 24
        self.assertEqual(detect(flat + [0.0] * 7 + [0.005])["tier"], "none")
        self.assertEqual(detect(flat + [0.0] * 7 + [0.05])["tier"], "3sigma")

    def test_needs_baseline(self):
        with self.assertRaises(ValueError):
            detect([1.0] * 10)


if __name__ == "__main__":
    unittest.main()
