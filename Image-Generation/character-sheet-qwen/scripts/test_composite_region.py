import unittest

from PIL import Image

from composite_region import composite


class RegionCompositeTests(unittest.TestCase):
    def test_pixels_outside_feathered_mask_remain_base(self):
        base = Image.new("RGB", (100, 100), "white")
        candidate = Image.new("RGB", (100, 100), "blue")
        result, mask = composite(base, candidate, (35, 35, 65, 65), 3)
        self.assertEqual(result.getpixel((50, 50)), (0, 0, 255))
        self.assertEqual(result.getpixel((0, 0)), (255, 255, 255))
        for y in range(100):
            for x in range(100):
                if mask.getpixel((x, y)) == 0:
                    self.assertEqual(result.getpixel((x, y)), base.getpixel((x, y)))

    def test_dimension_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "identical dimensions"):
            composite(Image.new("RGB", (100, 100)), Image.new("RGB", (50, 100)), (1, 1, 40, 90))

    def test_invalid_region_rejected(self):
        with self.assertRaisesRegex(ValueError, "inside"):
            composite(Image.new("RGB", (100, 100)), Image.new("RGB", (100, 100)), (1, 1, 120, 90))


if __name__ == "__main__":
    unittest.main()
