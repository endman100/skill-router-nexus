"""HTTP integration tests using empty text files and solid-color images only."""

import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from PIL import Image


SKILL = Path(__file__).resolve().parents[1]
SCRIPT = SKILL / 'scripts/eval_lora.py'
TEMPLATE = SKILL / 'templates/animaEndToEnd_fast.json'
WIDTH, HEIGHT = 96, 64


class FakeComfyUI(ThreadingHTTPServer):
    def __init__(self):
        super().__init__(('127.0.0.1', 0), Handler)
        self.visible = ['unit-000010.safetensors', 'unit.safetensors',
                        'unit-000005.safetensors']
        self.posts = []
        self.gets = []
        self.color = (32, 96, 160)
        self.history_polls = {}
        self.pending = False
        self.node_errors = False


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, payload, content_type='application/json'):
        data = json.dumps(payload).encode() if content_type == 'application/json' else payload
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        self.server.posts.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
        self.reply({'prompt_id': str(len(self.server.posts)),
                    'node_errors': {'x': {}} if self.server.node_errors else {}})

    def do_GET(self):
        self.server.gets.append(self.path)
        url = urlsplit(self.path)
        if url.path == '/object_info/LoraLoaderModelOnly':
            self.reply({'LoraLoaderModelOnly': {'input': {'required': {
                'lora_name': [self.server.visible]}}}})
        elif url.path.startswith('/history/'):
            prompt_id = url.path.rsplit('/', 1)[1]
            count = self.server.history_polls.get(prompt_id, 0) + 1
            self.server.history_polls[prompt_id] = count
            if count == 1 or self.server.pending:
                self.reply({})
            else:
                graph = self.server.posts[int(prompt_id) - 1]['prompt']
                save_id = next(key for key, node in graph.items()
                               if node['class_type'] == 'SaveImage')
                self.reply({prompt_id: {'outputs': {save_id: {'images': [{
                    'filename': 'solid color.png', 'subfolder': 'fake output', 'type': 'output'
                }]}}}})
        elif url.path == '/view':
            query = parse_qs(url.query)
            if query != {'filename': ['solid color.png'], 'subfolder': ['fake output'],
                         'type': ['output']}:
                self.send_error(400)
                return
            buffer = io.BytesIO()
            Image.new('RGB', (WIDTH, HEIGHT), self.server.color).save(buffer, format='PNG')
            self.reply(buffer.getvalue(), 'image/png')
        else:
            self.send_error(404)


class EvalLoraTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='lora validation ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run = self.root / 'run with spaces'
        self.models = self.run / 'models'
        self.models.mkdir(parents=True)
        for name in ('unit-000010.safetensors', 'unit.safetensors', 'unit-000005.safetensors'):
            (self.models / name).write_bytes(b'')
        (self.models / 'unit-000015-state').mkdir()
        (self.models / 'unit-000020.safetensors').mkdir()
        self.positive = self.root / 'positive file.txt'
        self.negative = self.root / 'negative file.txt'
        self.positive.write_text('', encoding='utf-8')
        self.negative.write_text('', encoding='utf-8')
        self.server = FakeComfyUI()
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.stop_server, thread)

    def stop_server(self, thread):
        self.server.shutdown()
        thread.join()
        self.server.server_close()

    def run_eval(self, *extra):
        return subprocess.run([
            sys.executable, '-B', str(SCRIPT), '--run-dir', str(self.run),
            '--prompt-file', str(self.positive), '--comfy-url',
            f'http://127.0.0.1:{self.server.server_port}',
            '--seeds', '42,7', '--width', str(WIDTH), '--height', str(HEIGHT),
            '--timeout', '5', *extra,
        ], cwd=self.root, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
            capture_output=True, text=True, timeout=15)

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_normal_flow_with_space_paths(self):
        self.assert_success(self.run_eval('--negative-file', str(self.negative)))
        self.assertEqual(len(self.server.posts), 8)
        meta = json.loads((self.run / 'lora_test/test_meta.json').read_text())
        self.assertEqual(meta['prompt_file'], str(self.positive))
        self.assertEqual(meta['negative_file'], str(self.negative))
        self.assertEqual(meta['prompt'], '')
        self.assertEqual(meta['negative'], '')
        self.assertEqual(meta['seeds'], [42, 7])
        self.assertEqual(meta['strength'], 0.8)
        self.assertEqual(meta['unet'], 'novaAnimeAM_v6029B.safetensors')
        self.assertEqual(meta['workflow'], str(TEMPLATE))
        self.assertEqual([entry['label'] for entry in meta['images']],
                         ['base', 'base', 'e5', 'e5', 'e10', 'e10', 'final', 'final'])
        for entry in meta['images']:
            path = Path(entry['output_path'])
            self.assertEqual(entry['dimensions'], [WIDTH, HEIGHT])
            self.assertEqual(entry['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(entry['file_size'], path.stat().st_size)
        with Image.open(self.run / 'checkpoint_comparison.png') as grid:
            self.assertEqual(grid.size, (80 + 2 * WIDTH, 32 + 4 * HEIGHT))
            self.assertEqual(grid.getpixel((80, 32)), self.server.color)
            # Row and column headers contain text on their white background.
            for box in ((0, 32, 80, 32 + HEIGHT), (80, 0, 80 + WIDTH, 32)):
                self.assertIsNotNone(grid.crop(box).convert('L').point(lambda p: 255 - p).getbbox())
        self.assertTrue(all(count == 2 for count in self.server.history_polls.values()))

    def test_skip_existing_without_prompt_requests(self):
        output = self.run / 'lora_test'
        output.mkdir()
        before = {}
        for label in ('base', 'e5', 'e10', 'final'):
            for seed in (42, 7):
                path = output / f'{label}_seed{seed}.png'
                Image.new('RGB', (WIDTH, HEIGHT), (80, 120, 160)).save(path)
                before[path] = (path.read_bytes(), path.stat().st_mtime_ns)
        self.assert_success(self.run_eval())
        self.assertEqual(self.server.posts, [])
        self.assertEqual(self.server.gets, ['/object_info/LoraLoaderModelOnly'])
        for path, original in before.items():
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), original)
        self.assertTrue((output / 'test_meta.json').is_file())
        self.assertTrue((self.run / 'checkpoint_comparison.png').is_file())

    def test_lora_not_visible(self):
        self.server.visible = ['unit.safetensors']
        result = self.run_eval()
        self.assertNotEqual(result.returncode, 0)
        for expected in ('unit-000005.safetensors', 'unit-000010.safetensors',
                         'extra_model_paths.yaml', str(self.models)):
            self.assertIn(expected, result.stderr)
        self.assertEqual(self.server.posts, [])
        self.assertFalse((self.run / 'lora_test').exists())

    def test_all_black_error(self):
        self.server.color = (0, 0, 0)
        result = self.run_eval()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('All-black', result.stderr)
        self.assertEqual(len(self.server.posts), 1)
        self.assertEqual(list((self.run / 'lora_test').iterdir()), [])

    def test_base_rewires_all_references_with_renamed_ids(self):
        graph = json.loads(TEMPLATE.read_text())
        graph['extra'] = {'class_type': 'ModelConsumer', 'inputs': {'model': ['67', 0]}}
        mapping = {key: f'node_{key}' for key in graph}
        renamed = {}
        for key, node in graph.items():
            for name, value in node['inputs'].items():
                if isinstance(value, list) and len(value) == 2:
                    node['inputs'][name] = [mapping[value[0]], value[1]]
            renamed[mapping[key]] = node
        custom = self.root / 'renamed workflow.json'
        custom.write_text(json.dumps(renamed))
        self.assert_success(self.run_eval('--workflow', str(custom), '--seeds', '42'))
        base = self.server.posts[0]['prompt']
        self.assertFalse(any(n['class_type'] == 'LoraLoaderModelOnly' for n in base.values()))
        self.assertEqual(base['node_19']['inputs']['model'], ['node_49', 0])
        self.assertEqual(base['node_extra']['inputs']['model'], ['node_49', 0])
        self.assertFalse(any(value == ['node_67', 0] for node in base.values()
                             for value in node['inputs'].values()))
        lora_graph = self.server.posts[1]['prompt']
        self.assertEqual(lora_graph['node_67']['inputs']['lora_name'], 'unit-000005.safetensors')
        self.assertEqual(lora_graph['node_67']['inputs']['strength_model'], 0.8)

    def test_no_base_and_parameter_overrides(self):
        self.assert_success(self.run_eval('--no-base', '--seeds', '123', '--strength', '0.6',
                                          '--unet', 'custom.safetensors', '--steps', '12',
                                          '--cfg', '3', '--sampler', 'test_sampler',
                                          '--scheduler', 'test_scheduler'))
        self.assertEqual(len(self.server.posts), 3)
        graph = self.server.posts[0]['prompt']
        self.assertEqual(graph['49']['inputs']['unet_name'], 'custom.safetensors')
        self.assertEqual(graph['67']['inputs']['strength_model'], 0.6)
        for key, value in {'seed': 123, 'steps': 12, 'cfg': 3,
                           'sampler_name': 'test_sampler', 'scheduler': 'test_scheduler'}.items():
            self.assertEqual(graph['19']['inputs'][key], value)
        self.assertEqual(graph['28']['inputs']['width'], WIDTH)
        self.assertEqual(graph['28']['inputs']['height'], HEIGHT)
        self.assertEqual(graph['11']['inputs']['text'], '')
        self.assertEqual(graph['12']['inputs']['text'], '')
        with Image.open(self.run / 'checkpoint_comparison.png') as grid:
            self.assertEqual(grid.size, (80 + WIDTH, 32 + 3 * HEIGHT))

    def test_dry_run_has_no_requests_or_writes(self):
        result = self.run_eval('--dry-run')
        self.assert_success(result)
        plan = json.loads(result.stdout)
        self.assertEqual([job['label'] for job in plan],
                         ['base', 'base', 'e5', 'e5', 'e10', 'e10', 'final', 'final'])
        self.assertEqual(plan[0]['seed'], 42)
        self.assertIsNone(plan[0]['lora_file'])
        self.assertEqual(plan[2]['lora_file'], str(self.models / 'unit-000005.safetensors'))
        self.assertEqual(plan[0]['output_path'], str(self.run / 'lora_test/base_seed42.png'))
        self.assertEqual(self.server.gets, [])
        self.assertEqual(self.server.posts, [])
        self.assertFalse((self.run / 'lora_test').exists())
        self.assertFalse((self.run / 'checkpoint_comparison.png').exists())

    def test_timeout(self):
        self.server.pending = True
        result = self.run_eval('--timeout', '0.5')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('timed out', result.stderr)
        self.assertEqual(len(self.server.posts), 1)

    def test_prompt_validation_error(self):
        self.server.node_errors = True
        result = self.run_eval()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('validation failed', result.stderr)
        self.assertEqual(self.server.history_polls, {})


if __name__ == '__main__':
    unittest.main()
