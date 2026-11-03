"""Native-alpha crop regressions."""
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
from compose_turnaround_sheet import alpha_bbox, crop_subject


class SubjectCropTests(unittest.TestCase):
    def test_preserves_pale_edges_holes_and_translucency(self):
        im = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        ImageDraw.Draw(im).rectangle((20, 10, 80, 90), fill=(255, 255, 255, 128))
        im.putpixel((40, 40), (0, 0, 0, 0))
        im.putpixel((2, 2), (100, 120, 140, 5))
        self.assertEqual(alpha_bbox(im), (2, 2, 81, 91))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "asset.png"
            im.save(path)
            crop = crop_subject(path)
        self.assertEqual(crop.mode, "RGBA")
        self.assertEqual(crop.getpixel((0, 0)), (100, 120, 140, 5))
        self.assertEqual(crop.getpixel((38, 38))[3], 0)
        self.assertEqual(crop.getpixel((18, 8)), (255, 255, 255, 128))

    def test_rejects_rgb_and_opaque_rgba(self):
        for im in (Image.new("RGB", (10, 10), "white"),
                   Image.new("RGBA", (10, 10), (255, 255, 255, 255))):
            with self.subTest(mode=im.mode), self.assertRaisesRegex(ValueError, "alpha|transparent"):
                alpha_bbox(im)

    def test_rejects_empty_asset(self):
        with self.assertRaisesRegex(ValueError, "fully transparent"):
            alpha_bbox(Image.new("RGBA", (10, 10), (0, 0, 0, 0)))
