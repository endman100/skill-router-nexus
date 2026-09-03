import copy
import math
import unittest

from estimate_character_height import resolve


class HeightResolutionTests(unittest.TestCase):
    def scale_input(self):
        return {
            "mode": "scale", "reason": "synthetic equal-scale known-length test",
            "reference_kind": "original", "geometry": "equal_scale",
            "landmarks": {"top_y": 100, "sole_y": 800},
            "reference_span_px": 140, "reference_cm": 30,
            "reference_cm_error": 0.1, "pixel_error": 1,
        }

    def test_known_ratio(self):
        self.assertEqual(resolve(self.scale_input())["height_cm"], 150)

    def test_resize_invariance(self):
        data = self.scale_input()
        expected = resolve(data)
        for factor in (0.5, 2, 10):
            changed = copy.deepcopy(data)
            changed["landmarks"] = {k: v * factor for k, v in data["landmarks"].items()}
            changed["reference_span_px"] *= factor
            changed["pixel_error"] *= factor
            actual = resolve(changed)
            self.assertEqual(actual["height_cm"], expected["height_cm"])
            self.assertEqual(actual["physical_height_interval_cm"], expected["physical_height_interval_cm"])

    def test_translation_invariance(self):
        data = self.scale_input()
        data["landmarks"] = {k: v + 731 for k, v in data["landmarks"].items()}
        self.assertEqual(resolve(data)["height_cm"], 150)

    def test_error_interval(self):
        low, high = resolve(self.scale_input())["physical_height_interval_cm"]
        self.assertLess(low, 150)
        self.assertGreater(high, 150)

    def test_generated_scale_rejected(self):
        data = self.scale_input()
        data["reference_kind"] = "generated"
        with self.assertRaises(ValueError):
            resolve(data)

    def test_perspective_without_rectification_rejected(self):
        data = self.scale_input()
        data["geometry"] = "unknown_depth"
        with self.assertRaises(ValueError):
            resolve(data)

    def test_head_ratio_does_not_produce_centimeters(self):
        data = {"mode": "unresolved", "reason": "No independent scale", "landmarks": {"top_y": 68, "chin_y": 542, "sole_y": 1473}}
        result = resolve(data)
        self.assertAlmostEqual(result["head_count"], 1405 / 474, places=5)
        self.assertIsNone(result["height_cm"])

    def test_same_proportions_allow_different_design_heights(self):
        data = {"mode": "design_prior", "reason": "Explicit setting", "landmarks": {"top_y": 68, "chin_y": 542, "sole_y": 1473}}
        for height in (120, 150, 180):
            result = resolve(dict(data, height_cm=height))
            self.assertEqual(result["height_cm"], height)
            self.assertIsNone(result["physical_height_cm"])
            self.assertEqual(result["confidence"], "not_measured")

    def test_repeated_inputs_are_identical(self):
        data = self.scale_input()
        self.assertEqual(resolve(data), resolve(copy.deepcopy(data)))

    def test_invalid_values(self):
        for value in (0, -1, math.nan, math.inf, True):
            data = self.scale_input()
            data["reference_span_px"] = value
            with self.assertRaises(ValueError):
                resolve(data)

    def test_missing_reason_rejected(self):
        data = self.scale_input()
        del data["reason"]
        with self.assertRaises(ValueError):
            resolve(data)

    def test_uncertainty_consuming_span_rejected(self):
        data = self.scale_input()
        data["pixel_error"] = 70
        with self.assertRaises(ValueError):
            resolve(data)


if __name__ == "__main__":
    unittest.main()
