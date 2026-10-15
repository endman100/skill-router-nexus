import json
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from qwen_asset import ROOT, build_graph, monitor, validate


class QwenAssetTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / "references/backend.json").read_text())

    def test_all_sixteen_refs_remain_ordered(self):
        names = [f"original-{n}.png" for n in range(16)]
        graph = build_graph(self.config, names, "instruction", "negative", "test")
        for i, name in enumerate(names, 1):
            link = graph["5"]["inputs"][f"images.image_{i}"]
            self.assertEqual(graph[link[0]]["inputs"]["image"], name)
        self.assertEqual(len(graph), 25)
        self.assertFalse(any("Lora" in n["class_type"] for n in graph.values()))

    def test_original_front_and_crop_use_distinct_ordered_inputs(self):
        graph = build_graph(self.config, ["original.jpg", "accepted-front.png", "shoe-crop.png"], "roles", "negative", "test")
        for slot, name in enumerate(["original.jpg", "accepted-front.png", "shoe-crop.png"], 1):
            node_id = graph["5"]["inputs"][f"images.image_{slot}"][0]
            self.assertEqual(graph[node_id]["inputs"]["image"], name)

    def test_validator_rejects_unavailable_model(self):
        schemas = {"UNETLoader": {"input": {"required": {"unet_name": [["available.safetensors"]], "weight_dtype": [["default"]]}}, "output": ["MODEL"]}}
        graph = {"1": {"class_type": "UNETLoader", "inputs": {"unet_name": "missing.safetensors", "weight_dtype": "default"}}}
        with self.assertRaisesRegex(ValueError, "unavailable value"):
            validate(graph, schemas)

    def test_validator_rejects_unknown_dynamic_slot(self):
        schemas = {"Encode": {"input": {"required": {"images": ["COMFY_AUTOGROW_V3", {"template": {"names": ["image_1"]}}]}}, "output": []}}
        with self.assertRaisesRegex(ValueError, "unknown input"):
            validate({"1": {"class_type": "Encode", "inputs": {"images.image_2": ["2", 0]}}}, schemas)

    def test_timeout_retains_job_without_cancel(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "candidate.png"
            log_path = output.with_suffix(".request.json")
            log = {"prompt_id": "existing"}
            with patch("qwen_asset.request") as req:
                with self.assertRaises(TimeoutError):
                    monitor("http://local", "existing", output, 0, log, log_path)
                req.assert_not_called()
            self.assertEqual(json.loads(log_path.read_text())["state"], "timeout_job_retained")

    def test_execution_error_is_not_completion(self):
        history = {"job": {"status": {"status_str": "error", "messages": [["execution_error", {"exception_message": "OOM"}]]}}}
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "candidate.png"
            with patch("qwen_asset.request", return_value=history):
                with self.assertRaisesRegex(RuntimeError, "execution failed"):
                    monitor("http://local", "job", output, 1, {}, output.with_suffix(".request.json"))
            self.assertFalse(output.exists())
            self.assertTrue(output.with_suffix(".history.json").exists())

    def test_success_downloads_only_matching_prompt_output(self):
        raw = io.BytesIO()
        Image.new("RGB", (32, 32), "white").save(raw, format="PNG")
        history = {"job": {"status": {"completed": True, "status_str": "success"}, "outputs": {"9": {"images": [{"filename": "result.png", "subfolder": "sheet", "type": "output"}]}}}}
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "candidate.png"
            with patch("qwen_asset.request", side_effect=[history, raw.getvalue()]) as req:
                monitor("http://local", "job", output, 1, {}, output.with_suffix(".request.json"))
                self.assertEqual(req.call_args_list[0].args[1], "/history/job")
                self.assertIn("filename=result.png", req.call_args_list[1].args[1])
            self.assertEqual(output.read_bytes(), raw.getvalue())
            self.assertEqual(json.loads(output.with_suffix(".request.json").read_text())["state"], "generated_needs_visual_review")


if __name__ == "__main__":
    unittest.main()
