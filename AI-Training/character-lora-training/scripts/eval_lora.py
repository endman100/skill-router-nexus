#!/usr/bin/env python3
"""Compare training checkpoints through the ComfyUI HTTP API."""

import argparse
import hashlib
import io
import json
import re
import shutil
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw, ImageFont

sys.dont_write_bytecode = True
from vocab_tools import feature_options, trait_field


ROW_HEADER = 80
COLUMN_HEADER = 32
TEMPLATES = Path(__file__).resolve().parent.parent / 'templates'
TEST_NAMES = ('reconstruction', 'scenario', 'showcase')


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--checkpoints', type=Path)
    parser.add_argument('--out-dir', type=Path)
    parser.add_argument('--comfy-url', default='http://127.0.0.1:1121')
    parser.add_argument('--workflow', type=Path)
    parser.add_argument('--trigger')
    parser.add_argument('--tests', default=','.join(TEST_NAMES),
                        help='Comma-separated tests: reconstruction, scenario, showcase (default: all)')
    parser.add_argument('--num-reconstruction', type=int, default=4)
    parser.add_argument('--scenario-template', type=Path,
                        default=TEMPLATES / 'validate_scenario_prompt.tmpl')
    parser.add_argument('--scenarios', type=Path,
                        default=TEMPLATES / 'validate_scenarios.txt')
    parser.add_argument('--outfit', choices=('change', 'keep', 'both'), default='both',
                        help='Showcase outfits: change, keep, or both (default: both, change then keep)')
    parser.add_argument('--showcase-template', type=Path,
                        default=TEMPLATES / 'showcase_prompt.tmpl')
    parser.add_argument('--showcase-change', type=Path,
                        default=TEMPLATES / 'showcase_change_outfit.txt')
    parser.add_argument('--showcase-keep', type=Path,
                        default=TEMPLATES / 'showcase_keep_outfit.txt')
    parser.add_argument('--character-features', type=Path)
    parser.add_argument('--vocab-params', type=Path)
    parser.add_argument('--seeds', default='31415926')
    parser.add_argument('--showcase-seed-base', type=int, default=31415926,
                        help='showcase seed = base + case_index*10000')
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
    args.tests = list(dict.fromkeys(t.strip() for t in args.tests.split(',') if t.strip()))
    unknown = [t for t in args.tests if t not in TEST_NAMES]
    if unknown or not args.tests:
        parser.error(f'--tests must be a comma-separated subset of {", ".join(TEST_NAMES)}; got {unknown or "(empty)"}')
    try:
        args.seeds = list(dict.fromkeys(int(s.strip()) for s in args.seeds.split(',')))
    except ValueError:
        parser.error('--seeds must be comma-separated integers')
    if min(args.width, args.height, args.steps, args.timeout) <= 0:
        parser.error('width, height, steps and timeout must be positive')
    return args


def checkpoints(models):
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


def prepare_workflow(args, lora, seed, positive):
    workflow = json.loads(args.workflow.read_text(encoding='utf-8'))
    sampler = workflow[unique_node(workflow, 'KSampler')]['inputs']
    unet_id = unique_node(workflow, 'UNETLoader')
    lora_id = unique_node(workflow, 'LoraLoaderModelOnly')
    workflow[unet_id]['inputs']['unet_name'] = args.unet
    encoder = workflow[sampler['positive'][0]]
    if encoder['class_type'] != 'CLIPTextEncode':
        raise ValueError('KSampler positive must link to CLIPTextEncode')
    encoder['inputs']['text'] = positive
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
            f'. Use ComfyUI extra_model_paths.yaml to point loras at {args.checkpoints}')


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


def workspace_defaults(args):
    args.workspace = args.workspace.resolve()
    validate = args.workspace / '07_validate'
    vocab = args.workspace / '05_caption' / 'vocab'
    args.checkpoints = (args.checkpoints or args.workspace / '06_train' / 'models').resolve()
    args.out_dir = (args.out_dir or validate).resolve()
    args.workflow = (args.workflow or (
        validate / 'workflow.json' if (validate / 'workflow.json').exists()
        else TEMPLATES / 'animaEndToEnd_fast.json')).resolve()
    default = validate / 'prompts' / 'character_features.txt'
    value = args.character_features
    args.character_features = (value or default).resolve() if value or default.exists() else None
    args.vocab_params = (args.vocab_params or (
        vocab / 'caption_vocab_params.json' if (vocab / 'caption_vocab_params.json').exists()
        else TEMPLATES / 'caption_vocab_params.json')).resolve()
    args.scenario_template = args.scenario_template.resolve()
    args.scenarios = args.scenarios.resolve()
    args.showcase_template = args.showcase_template.resolve()
    args.showcase_change = args.showcase_change.resolve()
    args.showcase_keep = args.showcase_keep.resolve()


def infer_trigger(train):
    manifest = train / 'manifest.json'
    if manifest.exists():
        trigger = json.loads(manifest.read_text(encoding='utf-8')).get('trigger')
        if trigger:
            return trigger
    for path in sorted(train.glob('*.txt'), key=lambda p: (len(p.name), p.name)):
        tokens = path.read_text(encoding='utf-8').strip().split(',')
        index = 1 if tokens[0].strip() == 'anime style' else 0
        if len(tokens) > index and tokens[index].strip():
            return tokens[index].strip()
    raise ValueError(f'Cannot infer trigger from {train}; use --trigger')


def reconstruction_cases(train, reference, count, dry_run):
    order = lambda p: (len(p.name), p.name)
    present = {p.name: p for p in sorted(reference.glob('*.png'), key=order) if p.is_file()}
    copies = {}
    if len(present) < count:
        for path in sorted(train.glob('*.png'), key=order):
            if (not path.is_file() or not path.with_suffix('.txt').is_file()
                    or path.name in present):
                continue
            present[path.name] = path
            copies[path.name] = path
            if len(present) >= count:
                break
        originals = sorted(present, key=lambda name: (len(name), name))
        if not originals and count > 0:
            raise ValueError(f'No reconstruction image/caption pairs in {train}')
        index = 0
        while len(present) < count:
            name = originals[index % len(originals)]
            target = f'{Path(name).stem}_{index}_copy.png'
            index += 1
            if target in present:
                continue
            present[target] = present[name]
            copies[target] = present[name]
    if not dry_run:
        reference.mkdir(parents=True, exist_ok=True)
        for name, source in copies.items():
            shutil.copyfile(source, reference / name)
            shutil.copyfile(source.with_suffix('.txt'), (reference / name).with_suffix('.txt'))
    return [{'case': Path(name).stem, 'reference': str(reference / name),
             'source_file': str(present[name]),
             'prompt': present[name].with_suffix('.txt').read_text(encoding='utf-8').strip()}
            for name in sorted(present, key=lambda name: (len(name), name))[:count]]


def character_features(args):
    if args.character_features:
        return args.character_features.read_text(encoding='utf-8').strip(), args.character_features
    vocab_path = args.workspace / '05_caption' / 'vocab' / 'vocab.json'
    vocab = json.loads(vocab_path.read_text(encoding='utf-8'))
    fields = json.loads(args.vocab_params.read_text(encoding='utf-8'))['field_traits']
    excluded = {'character_clothing_tags'}
    features = [f for f in vocab['character_features']
                if trait_field(f['trait'], fields) not in excluded]
    options = feature_options(features, fields)
    outfit_path = vocab_path.parent / 'main_outfit.json'
    outfit = json.loads(outfit_path.read_text(encoding='utf-8')) if outfit_path.exists() else {}
    outfit_tags = {item['tag'] if isinstance(item, dict) else item for item in outfit.get('tags', [])}
    tags = [item['tag'] for field in fields if field not in excluded
            for item in options[field] if item['tag'] not in outfit_tags]
    return ', '.join(dict.fromkeys(tags)), vocab_path


def scenario_cases(args):
    features, source = character_features(args)
    template = args.scenario_template.read_text(encoding='utf-8')
    cases = []
    with args.scenarios.open(encoding='utf-8') as lines:
        for line in lines:
            scenario = line.strip()
            if not scenario:
                continue
            index = len(cases)
            prompt = template.replace('{trigger}', args.trigger).replace(
                '{character_features}', features).replace('{scenario}', scenario)
            cases.append({'index': index, 'case': f's{index:02d}', 'scenario': scenario,
                          'seed': 31415926 + index * 10000, 'prompt': prompt})
    return {'trigger': args.trigger, 'character_features': features,
            'character_features_source': str(source), 'template': str(args.scenario_template),
            'scenarios': str(args.scenarios), 'cases': cases}


def showcase_cases(args, outfit):
    features, source = character_features(args)
    template = args.showcase_template.read_text(encoding='utf-8').strip()
    data_file = args.showcase_change if outfit == 'change' else args.showcase_keep
    metadata = {'trigger': args.trigger, 'character_features': features,
                'character_features_source': str(source), 'outfit': outfit,
                'template': str(args.showcase_template), 'data_file': str(data_file),
                'showcase_seed_base': args.showcase_seed_base}
    if outfit == 'keep':
        outfit_source = args.workspace / '07_validate' / 'prompts' / 'main_outfit_tags.txt'
        outfit_json = args.workspace / '05_caption' / 'vocab' / 'main_outfit.json'
        if outfit_source.exists():
            outfit_tags = [tag.strip() for tag in re.split(
                r'[,\n]', outfit_source.read_text(encoding='utf-8')) if tag.strip()]
        elif outfit_json.exists():
            outfit_source = outfit_json
            tags = json.loads(outfit_source.read_text(encoding='utf-8'))['tags']
            outfit_tags = [item['tag'] if isinstance(item, dict) else item for item in tags]
        else:
            raise ValueError(f'Missing outfit tags: {outfit_source} or {outfit_json}')
        metadata.update(outfit_tags=outfit_tags, outfit_source=str(outfit_source))
    with args.showcase_keep.open(encoding='utf-8') as lines:
        scenes = [line.strip() for line in lines if line.strip()]
    with data_file.open(encoding='utf-8') as lines:
        rows = [line.strip() for line in lines if line.strip()]
    cases = []
    for index, (row, scene) in enumerate(zip(rows, scenes)):
        cloth = (', '.join(outfit_tags) if outfit == 'keep'
                 else row[:-len(scene)].strip().rstrip(',').strip())
        other = 'solo_focus, human focus, ' + scene
        prompt = template.replace('{trigger}', args.trigger).replace(
            '{character_features}', features.strip().rstrip(',')).replace(
            '{cloth_feature}', cloth).replace('{other}', other)
        seed = args.showcase_seed_base + index * 10000
        cases.append({'index': index, 'case': f'c{index:02d}', 'showcase': row,
                      'cloth_feature': cloth, 'other': other, 'seed': seed, 'prompt': prompt})
    return {**metadata, 'cases': cases}


def comparison(args, rows, test_dir, columns, references=None):
    display_rows = ([('reference', None)] if references is not None else []) + rows
    for start in range(0, len(columns), 6):
        chunk = columns[start:start + 6]
        grid = Image.new('RGB', (ROW_HEADER + args.width * len(chunk),
                                 COLUMN_HEADER + args.height * len(display_rows)), 'white')
        draw = ImageDraw.Draw(grid)
        font = ImageFont.load_default()
        for column, (case, seed) in enumerate(chunk):
            x = ROW_HEADER + column * args.width
            draw.text((x + 4, 4), f'{case}\nseed{seed}', font=font, fill='black')
        for row, (label, _) in enumerate(display_rows):
            y = COLUMN_HEADER + row * args.height
            draw.text((4, y + 8), label, font=font, fill='black')
            for column, (case, seed) in enumerate(chunk):
                path = (Path(references[case]) if label == 'reference' else
                        test_dir / 'lora_test' / f'{label}_{case}_seed{seed}.png')
                with Image.open(path) as image:
                    tile = image.convert('RGB')
                    tile.thumbnail((args.width, args.height))
                    grid.paste(tile, (ROW_HEADER + column * args.width, y))
        grid.save(test_dir / f'checkpoint_comparison_{start // 6 + 1:02d}.png')


def main():
    args = parse_args()
    try:
        workspace_defaults(args)
        train = args.workspace / '05_caption' / 'train_set'
        args.trigger = args.trigger or infer_trigger(train)
        loras = checkpoints(args.checkpoints)
        rows = ([] if args.no_base else [('base', None)]) + loras
        reference = args.out_dir / 'reconstruction' / 'reference'
        reconstruction = []
        workloads = []
        if 'reconstruction' in args.tests:
            reconstruction = reconstruction_cases(train, reference, args.num_reconstruction, True)
            workloads.append({'key': 'reconstruction', 'name': 'reconstruction',
                              'dir': args.out_dir / 'reconstruction', 'cases': reconstruction,
                              'prompts': None})
        if 'scenario' in args.tests:
            built = scenario_cases(args)
            workloads.append({'key': 'scenario', 'name': 'scenario',
                              'dir': args.out_dir / 'scenario', 'cases': built['cases'],
                              'prompts': built})
        if 'showcase' in args.tests:
            modes = ('change', 'keep') if args.outfit == 'both' else (args.outfit,)
            for outfit in modes:
                built = showcase_cases(args, outfit)
                workloads.append({
                    'key': f'showcase_{outfit}' if len(modes) > 1 else 'showcase',
                    'name': 'showcase', 'dir': args.out_dir / f'showcase_{outfit}',
                    'cases': built['cases'], 'prompts': built})
        tests = {}
        for workload in workloads:
            name = workload['name']
            jobs = [{'test': name, 'label': label, 'case': case['case'], 'seed': seed,
                     'lora_file': str(lora) if lora else None, 'output_path': str(
                         workload['dir'] / 'lora_test' / f"{label}_{case['case']}_seed{seed}.png"),
                     'prompt': case['prompt']}
                    for label, lora in rows for case in workload['cases']
                    for seed in (args.seeds if name == 'reconstruction' else [case['seed']])]
            workload['jobs'] = jobs
            tests[workload['key']] = {'jobs': jobs, 'job_count': len(jobs)}
        references = [{'case': case['case'], 'image': case['reference'],
                       'caption': str(Path(case['reference']).with_suffix('.txt')),
                       'source_file': case['source_file']} for case in reconstruction]
        if args.dry_run:
            print(json.dumps({'trigger': args.trigger, 'workflow': str(args.workflow),
                              'checkpoints': [{'label': label, 'lora_file': str(path)}
                                              for label, path in loras],
                              'reference_files': references, 'selected_tests': args.tests, 'tests': tests,
                              'total_jobs': sum(test['job_count'] for test in tests.values())},
                             ensure_ascii=False, indent=2))
            return 0
        workflow = json.loads(args.workflow.read_text(encoding='utf-8'))
        sampler = workflow[unique_node(workflow, 'KSampler')]['inputs']
        negative = workflow[sampler['negative'][0]]['inputs']['text']
        confirm_loras(args, loras)
        if 'reconstruction' in tests:
            reconstruction_cases(train, reference, args.num_reconstruction, False)
        for workload in workloads:
            name = workload['name']
            test_dir = workload['dir']
            jobs = workload['jobs']
            (test_dir / 'lora_test').mkdir(parents=True, exist_ok=True)
            if workload['prompts'] is not None:
                (test_dir / 'prompts.json').write_text(
                    json.dumps(workload['prompts'], ensure_ascii=False, indent=2) + '\n',
                    encoding='utf-8')
            entries = []
            for job in jobs:
                path = Path(job['output_path'])
                if not path.exists():
                    lora = Path(job['lora_file']) if job['lora_file'] else None
                    workflow = prepare_workflow(args, lora, job['seed'], job['prompt'])
                    payload = render(args, workflow)
                    with Image.open(io.BytesIO(payload)) as image:
                        rgb = image.convert('RGB')
                        if all(high == 0 for _, high in rgb.getextrema()):
                            raise ValueError(f'All-black image returned for {path.name}')
                        rgb.save(path, format='PNG')
                entries.append({**job, **inspect_image(path)})
            meta = {'trigger': args.trigger, 'selected_tests': args.tests,
                    'negative': negative, 'seeds': list(dict.fromkeys(j['seed'] for j in jobs)),
                    'strength': args.strength, 'workflow': str(args.workflow), 'unet': args.unet,
                    'width': args.width, 'height': args.height, 'steps': args.steps, 'cfg': args.cfg,
                    'sampler': args.sampler, 'scheduler': args.scheduler, 'images': entries}
            if name == 'reconstruction':
                meta['reference_files'] = references
            elif name == 'showcase':
                meta.update({key: value for key, value in workload['prompts'].items() if key != 'cases'})
            (test_dir / 'test_meta.json').write_text(
                json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            columns = [(case['case'], seed) for case in workload['cases']
                       for seed in (args.seeds if name == 'reconstruction' else [case['seed']])]
            comparison(args, rows, test_dir, columns,
                       {case['case']: case['reference'] for case in reconstruction}
                       if name == 'reconstruction' else None)
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
