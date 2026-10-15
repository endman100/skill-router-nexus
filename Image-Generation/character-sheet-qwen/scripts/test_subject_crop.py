"""White-margin regressions; no generator or real-person measurements involved."""
import unittest
from PIL import Image, ImageDraw
from compose_turnaround_sheet import foreground_bbox, on_white


class SubjectCropTests(unittest.TestCase):
    def test_faint_garment_extent_is_preserved(self):
        im = Image.new("RGB", (100, 100), "white")
        draw = ImageDraw.Draw(im)
        draw.rectangle((20, 10, 80, 90), fill=(245, 245, 245))
        draw.rectangle((35, 30, 65, 70), fill=(50, 50, 50))
        self.assertEqual(foreground_bbox(im), (20, 10, 81, 91))

    def test_near_white_noise_does_not_expand_crop(self):
        im = Image.new("RGB", (100, 100), (253, 253, 253))
        ImageDraw.Draw(im).rectangle((20, 10, 80, 90), fill=(245, 245, 245))
        im.putpixel((2, 2), (248, 248, 248))
        self.assertEqual(foreground_bbox(im), (20, 10, 81, 91))

    def test_thin_dark_hair_is_preserved(self):
        im = Image.new("RGB", (100, 100), "white")
        ImageDraw.Draw(im).line((20, 10, 80, 90), fill="black", width=1)
        self.assertEqual(foreground_bbox(im), (20, 10, 81, 91))

    def test_generated_background_variation_does_not_count_as_subject(self):
        im = Image.new("RGB", (100, 100), (250, 252, 251))
        ImageDraw.Draw(im).rectangle((20, 10, 80, 90), fill=(248, 248, 248))
        self.assertEqual(foreground_bbox(im), (20, 10, 81, 91))

    def test_transparent_black_does_not_become_background(self):
        im = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        ImageDraw.Draw(im).rectangle((20, 10, 80, 90), fill=(245, 245, 245, 255))
        self.assertEqual(foreground_bbox(im), (20, 10, 81, 91))
        self.assertEqual(on_white(im).getpixel((0, 0)), (255, 255, 255))

    def test_empty_image_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "No non-white"):
            foreground_bbox(Image.new("RGB", (100, 100), "white"))


if __name__ == "__main__":
    unittest.main()
