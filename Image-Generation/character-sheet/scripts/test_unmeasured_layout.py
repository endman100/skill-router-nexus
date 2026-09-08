"""Regression tests for the reusable, ruler-free default layout."""
import copy
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

from compose_unmeasured_sheet import compose
from verify_turnaround_sheet import verify_unmeasured


class UnmeasuredLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = json.loads((Path(__file__).parents[1] / "references/config.example.json").read_text())
        self.config.update(canvas_height_px=360, body_margin_px=10, grid_column_width_px=240)
        for name, width in (("front", 80), ("profile", 65), ("back", 105)):
            im = Image.new("RGB", (width+20, 220), "white")
            ImageDraw.Draw(im).rectangle((10, 10, width+9, 209), fill="#456789")
            im.save(self.root / f"{name}.png")
        for name, color in (("detail-hands", "#996633"), ("detail-feet", "#333333"), ("detail-outfit", "#663399")):
            im = Image.new("RGB", (140, 120), "white")
            ImageDraw.Draw(im).rectangle((10, 10, 129, 109), fill=color)
            im.save(self.root / f"{name}.png")
        for i, color in enumerate(("#882222", "#224488", "#446622"), 1):
            im = Image.new("RGB", (120, 140), "white")
            ImageDraw.Draw(im).ellipse((10, 10, 109, 129), fill=color)
            im.save(self.root / f"expression-{i}.png")
        shutil.copyfile(self.root / "expression-3.png", self.root / "identity-anchor.png")

    def render(self, config=None):
        config = self.config if config is None else config
        im, data = compose(self.root, config)
        path = self.root / "config.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        data["config"] = str(path)
        return im, data

    def verify(self, im, data):
        with contextlib.redirect_stdout(io.StringIO()):
            verify_unmeasured(im, data)

    def test_default_without_mode_is_unmeasured(self):
        config = copy.deepcopy(self.config)
        del config["layout_mode"]
        im, data = self.render(config)
        self.assertIsNone(data["ruler"])
        self.assertEqual(data["body_data"], [])
        self.assertEqual(data["grid"]["columns"], 5)
        self.assertEqual(data["grid"]["rows"], 3)
        self.verify(im, data)

    def test_assets_occupy_requested_grid_spans(self):
        im, data = self.render()
        width = data["grid"]["column_width_px"]
        row = data["grid"]["row_edges_px"][1]
        self.assertEqual([entry["cell"] for entry in data["details"].values()], [
            [0, 0, width, row], [width, 0, width * 2, row], [width * 2, 0, width * 3, row],
        ])
        self.assertEqual([entry["cell"] for entry in data["expressions"].values()], [
            [width * 3, 0, width * 4, row], [width * 4, 0, width * 5, row],
        ])
        self.assertEqual(data["neutral_portrait"]["cell"], [width * 3, row, width * 5, im.height])
        self.assertEqual([entry["panel_box"] for entry in data["body_views"].values()], [
            [0, row, width, im.height], [width, row, width * 2, im.height], [width * 2, row, width * 3, im.height],
        ])
        self.assertEqual(im.getpixel((width * 4, row // 2)), (51, 51, 51))
        self.assertNotEqual(im.getpixel((width * 4, row + 10)), (51, 51, 51))
        self.verify(im, data)

    def test_stale_metric_fields_do_not_change_pixels(self):
        expected, _ = self.render()
        config = dict(self.config, height_cm=120, height_source="design_prior", body_data=["Weight: 40 kg"])
        actual, data = self.render(config)
        self.assertIsNone(ImageChops.difference(expected, actual).getbbox())
        self.verify(actual, data)

    def test_wide_body_expands_without_squeezing(self):
        im = Image.new("RGB", (420, 220), "white")
        ImageDraw.Draw(im).rectangle((10, 10, 409, 209), fill="#456789")
        im.save(self.root / "back.png")
        im, data = self.render()
        self.assertEqual(data["body_views"]["back"]["placed_box"][2] - data["body_views"]["back"]["placed_box"][0], 440)
        self.assertEqual(im.width, (440 + 32) * 5)
        self.verify(im, data)

    def test_repeated_render_is_identical(self):
        first, a = self.render()
        second, b = self.render()
        self.assertEqual(a, b)
        self.assertIsNone(ImageChops.difference(first, second).getbbox())

    def test_neutral_portrait_must_be_unchanged_anchor(self):
        shutil.copyfile(self.root / "expression-1.png", self.root / "expression-3.png")
        with self.assertRaisesRegex(ValueError, "NORMAL"):
            self.render()

    def test_duplicate_names_rejected(self):
        self.config["views"][1]["name"] = "front"
        with self.assertRaisesRegex(ValueError, "unique"):
            self.render()

    def test_invalid_dimensions_rejected(self):
        for key, value in (("canvas_height_px", True), ("body_margin_px", 200), ("panel_side_padding_px", -1), ("grid_column_width_px", 0)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.render(dict(self.config, **{key: value}))

    def test_exported_pixel_tampering_detected(self):
        im, data = self.render()
        im.putpixel((0, 0), (255, 0, 0))
        with self.assertRaisesRegex(AssertionError, "Exported pixels"):
            self.verify(im, data)

    def test_expression_cell_shift_detected(self):
        im, data = self.render()
        data["expressions"]["angry"]["cell"][1] += 1
        with self.assertRaisesRegex(AssertionError, "expression cell"):
            self.verify(im, data)

    def test_source_change_detected(self):
        im, data = self.render()
        shutil.copyfile(self.root / "back.png", self.root / "front.png")
        with self.assertRaisesRegex(AssertionError, "source changed"):
            self.verify(im, data)


if __name__ == "__main__":
    unittest.main()
