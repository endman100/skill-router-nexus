#!/usr/bin/env python3
"""Compare training checkpoints through the ComfyUI HTTP API."""

import argparse
import hashlib
import io
import json
import re
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw, ImageFont


ROW_HEADER = 80
COLUMN_HEADER = 32


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--comfy-url', default='http://127.0.0.1:1121')
    parser.add_argument('--workflow', type=Path, default=(
        Path(__file__).resolve().parent / '../templates/animaEndToEnd_fast.json'))
    parser.add_argument('--prompt-file', type=Path, required=True)
    parser.add_argument('--negative-file', type=Path)
    parser.add_argument('--seeds', default='31415926,42,1234567,20261022')
    parser.add_argument('--strength', type=float, default=0.8)
    parser.add_argument('--unet', default='novaAnimeAM_v6029B.safetensors')
    parser.add_argument('--width', type=int, default=720)
    parser.add_argument('--height', type=int, default=1280)
    parser.add_argument('--steps', type=int, default=40)
    parser.add_argument('--cfg', type=float, default=4)
    parser.add_argument('--sampler', default='er_sde')
    parser.add_argument('--scheduler', default='simple')
    parser.add_argument('--no-base', action='store_true')
    parser.add_argument('--timeout', type=float, default=600,
                        help='Seconds per image (default: 600)')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    try:
        args.seeds = list(dict.fromkeys(int(s.strip()) for s in args.seeds.split(',')))
    except ValueError:
        parser.error('--seeds must be comma-separated integers')
    if min(args.width, args.height, args.steps, args.timeout) <= 0:
        parser.error('width, height, steps and timeout must be positive')
    return args


def checkpoints(run_dir):
    models = run_dir / 'models'
    if not models.is_dir():
        raise ValueError(f'Missing models directory: {models}')
    found = []
    for path in models.glob('*.safetensors'):
        if not path.is_file():
            continue
        match = re.search(r'-(\d+)$', path.stem)
        epoch = int(match[1]) if match else None
        found.append((epoch, path))
    found.sort(key=lambda item: (item[0] is None, item[0] or 0, item[1].name))
    rows = [(f'e{epoch}' if epoch is not None else 'final', path)
            for epoch, path in found]
    if not rows:
        raise ValueError(f'No LoRA files found in {models}')
    if len({label for label, _ in rows}) != len(rows):
        raise ValueError('Multiple LoRA files have the same epoch/final label')
    return rows


def unique_node(workflow, class_type):
    matches = [key for key, node in workflow.items()
               if node['class_type'] == class_type]
    if len(matches) != 1:
        raise ValueError(f'Expected one {class_type} node, found {len(matches)}')
    return matches[0]


def prepare_workflow(args, lora, seed, positive, negative):
    workflow = json.loads(args.workflow.read_text(encoding='utf-8'))
    sampler = workflow[unique_node(workflow, 'KSampler')]['inputs']
    unet_id = unique_node(workflow, 'UNETLoader')
    lora_id = unique_node(workflow, 'LoraLoaderModelOnly')
    workflow[unet_id]['inputs']['unet_name'] = args.unet
    for key, text in (('positive', positive), ('negative', negative)):
        encoder = workflow[sampler[key][0]]
        if encoder['class_type'] != 'CLIPTextEncode':
            raise ValueError(f'KSampler {key} must link to CLIPTextEncode')
        encoder['inputs']['text'] = text
    latent = workflow[sampler['latent_image'][0]]
    if latent['class_type'] != 'EmptyLatentImage':
        raise ValueError('KSampler latent_image must link to EmptyLatentImage')
    latent['inputs'].update(width=args.width, height=args.height)
    sampler.update(seed=seed, steps=args.steps, cfg=args.cfg,
                   sampler_name=args.sampler, scheduler=args.scheduler)
    if lora is None:
        del workflow[lora_id]
        for node in workflow.values():
            for key, value in node['inputs'].items():
                if isinstance(value, list) and len(value) == 2 and value[0] == lora_id:
                    node['inputs'][key] = [unet_id, 0]
    else:
        workflow[lora_id]['inputs'].update(
            lora_name=lora.name, strength_model=args.strength)
    return workflow


def request(base, route, timeout, body=None, raw=False):
    data = None if body is None else json.dumps(body).encode('utf-8')
    req = Request(base.rstrip('/') + route, data=data,
                  headers={'Content-Type': 'application/json'} if data else {})
    with urlopen(req, timeout=timeout) as response:
        payload = response.read()
    return payload if raw else json.loads(payload)


def confirm_loras(args, rows):
    info = request(args.comfy_url, '/object_info/LoraLoaderModelOnly', args.timeout)
    options = info['LoraLoaderModelOnly']['input']['required']['lora_name'][0]
    missing = [path.name for _, path in rows if path.name not in options]
    if missing:
        raise ValueError(
            'LoRA files not visible in ComfyUI: ' + ', '.join(missing) +
            f'. Use ComfyUI extra_model_paths.yaml to point loras at {args.run_dir / "models"}')


def render(args, workflow):
    deadline = time.monotonic() + args.timeout

    def remaining():
        seconds = deadline - time.monotonic()
        if seconds <= 0:
            raise TimeoutError(f'Image timed out after {args.timeout} seconds')
        return seconds

    queued = request(args.comfy_url, '/prompt', remaining(),
                     {'prompt': workflow, 'client_id': str(uuid.uuid4())})
    if queued.get('error') or queued.get('node_errors'):
        raise ValueError(f'ComfyUI prompt validation failed: {queued}')
    prompt_id = queued['prompt_id']
    output_ids = [key for key, node in workflow.items()
                  if node['class_type'] == 'SaveImage']
    while True:
        history = request(args.comfy_url, '/history/' + quote(str(prompt_id), safe=''),
                          remaining()).get(prompt_id, {})
        if history.get('status', {}).get('status_str') == 'error':
            raise ValueError(f'ComfyUI execution failed for {prompt_id}')
        outputs = history.get('outputs', {})
        for key in output_ids:
            for item in outputs.get(key, {}).get('images', []):
                query = urlencode({k: item.get(k, '')
                                   for k in ('filename', 'subfolder', 'type')})
                return request(args.comfy_url, '/view?' + query, remaining(), raw=True)
        time.sleep(min(0.2, remaining()))


def inspect_image(path):
    payload = path.read_bytes()
    with Image.open(io.BytesIO(payload)) as image:
        rgb = image.convert('RGB')
        if all(high == 0 for _, high in rgb.getextrema()):
            raise ValueError(f'All-black image: {path}')
        dimensions = list(image.size)
    return {'sha256': hashlib.sha256(payload).hexdigest(),
            'file_size': len(payload), 'dimensions': dimensions}


def comparison(args, rows):
    grid = Image.new('RGB', (ROW_HEADER + args.width * len(args.seeds),
                             COLUMN_HEADER + args.height * len(rows)), 'white')
    draw = ImageDraw.Draw(grid)
    font = ImageFont.load_default()
    for column, seed in enumerate(args.seeds):
        x = ROW_HEADER + column * args.width
        draw.text((x + 4, 8), str(seed), font=font, fill='black')
    for row, (label, _) in enumerate(rows):
        y = COLUMN_HEADER + row * args.height
        draw.text((4, y + 8), label, font=font, fill='black')
        for column, seed in enumerate(args.seeds):
            path = args.run_dir / 'lora_test' / f'{label}_seed{seed}.png'
            with Image.open(path) as image:
                tile = image.convert('RGB')
                tile.thumbnail((args.width, args.height))
                grid.paste(tile, (ROW_HEADER + column * args.width, y))
    grid.save(args.run_dir / 'checkpoint_comparison.png')


def main():
    args = parse_args()
    try:
        args.run_dir = args.run_dir.resolve()
        args.workflow = args.workflow.resolve()
        args.prompt_file = args.prompt_file.resolve()
        positive = args.prompt_file.read_text(encoding='utf-8')
        negative = ''
        if args.negative_file:
            args.negative_file = args.negative_file.resolve()
            negative = args.negative_file.read_text(encoding='utf-8')
        loras = checkpoints(args.run_dir)
        rows = ([] if args.no_base else [('base', None)]) + loras
        output_dir = args.run_dir / 'lora_test'
        jobs = [{'label': label, 'lora_file': str(lora) if lora else None,
                 'seed': seed, 'output_path': str(output_dir / f'{label}_seed{seed}.png')}
                for label, lora in rows for seed in args.seeds]
        if args.dry_run:
            print(json.dumps(jobs, ensure_ascii=False, indent=2))
            return 0
        confirm_loras(args, loras)
        output_dir.mkdir(parents=True, exist_ok=True)
        entries = []
        for job in jobs:
            path = Path(job['output_path'])
            if not path.exists():
                lora = Path(job['lora_file']) if job['lora_file'] else None
                workflow = prepare_workflow(args, lora, job['seed'], positive, negative)
                payload = render(args, workflow)
                with Image.open(io.BytesIO(payload)) as image:
                    rgb = image.convert('RGB')
                    if all(high == 0 for _, high in rgb.getextrema()):
                        raise ValueError(f'All-black image returned for {path.name}')
                    rgb.save(path, format='PNG')
            entries.append({**job, **inspect_image(path)})
        meta = {'prompt_file': str(args.prompt_file), 'prompt': positive,
                'negative_file': str(args.negative_file) if args.negative_file else None,
                'negative': negative, 'seeds': args.seeds, 'strength': args.strength,
                'workflow': str(args.workflow), 'unet': args.unet, 'images': entries}
        (output_dir / 'test_meta.json').write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        comparison(args, rows)
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
