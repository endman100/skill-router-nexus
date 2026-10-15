"""Generate a full sheet or edit target using explicit prompts, without asset templates."""
import argparse
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from qwen_asset import ROOT, save, digest, request, upload, build_graph, validate, monitor


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--backend', type=Path, default=ROOT / 'references/backend.json')
    p.add_argument('--references', nargs='+', type=Path)
    p.add_argument('--prompt-file', type=Path)
    p.add_argument('--negative-file', type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--run', action='store_true')
    p.add_argument('--resume', action='store_true')
    p.add_argument('--timeout', type=float, default=2400)
    a = p.parse_args()
    out = a.output.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    log_path = out.with_suffix('.request.json')
    if out.exists():
        p.error('Output exists; retain it and choose a new filename')
    if a.resume:
        log = json.loads(log_path.read_text(encoding='utf-8-sig'))
        monitor(log['backend']['base_url'], log['prompt_id'], out, a.timeout, log, log_path)
        return
    if not a.references or not a.prompt_file:
        p.error('--references and --prompt-file are required')
    if log_path.exists() and json.loads(log_path.read_text(encoding='utf-8-sig'))['state'] != 'prepared':
        p.error('Existing submission; use --resume or a new output')
    config = json.loads(a.backend.read_text(encoding='utf-8-sig'))
    if any(config[k] < 32 or config[k] % 32 for k in ('width', 'height')):
        p.error('Dimensions must be positive multiples of 32')
    paths = [x.resolve(strict=True) for x in a.references]
    if len(paths) > 16:
        p.error('At most 16 references including edit targets')
    from PIL import Image
    for path in paths:
        with Image.open(path) as im:
            im.verify()
    prompt = a.prompt_file.read_text(encoding='utf-8-sig')
    negative = a.negative_file.read_text(encoding='utf-8-sig') if a.negative_file else ''
    base = config['base_url']
    schemas = request(base, '/object_info')
    entries = [{'path': str(x), 'sha256': digest(x), 'image_index': i+1} for i, x in enumerate(paths)]
    prefix = 'character-sheet-qwen/sheet-' + uuid.uuid4().hex
    graph = build_graph(config, [x.name for x in paths], prompt, negative, prefix)
    validate(graph, schemas)
    log = {'created_at': datetime.now(timezone.utc).isoformat(), 'state': 'prepared',
           'mode': 'explicit-full-sheet-or-edit', 'backend': config,
           'runtime': request(base, '/system_stats'), 'references': entries,
           'prompt': prompt, 'negative_prompt': negative, 'client_id': str(uuid.uuid4())}
    save(out.with_suffix('.api.json'), graph)
    save(out.with_suffix('.inventory.json'), entries)
    save(log_path, log)
    if not a.run:
        print('Schema validated; no upload or submission')
        return
    for entry, path in zip(entries, paths):
        entry['server_image'] = upload(base, path)
        save(log_path, log)
    graph = build_graph(config, [x['server_image'] for x in entries], prompt, negative, prefix)
    validate(graph, request(base, '/object_info'), uploaded=True)
    save(out.with_suffix('.api.json'), graph)
    save(out.with_suffix('.inventory.json'), entries)
    log['state'] = 'submitting_outcome_unknown'
    save(log_path, log)
    result = request(base, '/prompt', {'prompt': graph, 'client_id': log['client_id']})
    log.update(submission=result, prompt_id=result.get('prompt_id'),
               state='validation_failed' if result.get('node_errors') or not result.get('prompt_id') else 'queued')
    save(log_path, log)
    if log['state'] == 'validation_failed':
        raise RuntimeError(result)
    print('Queued ' + log['prompt_id'], flush=True)
    monitor(base, log['prompt_id'], out, a.timeout, log, log_path)


if __name__ == '__main__':
    main()
