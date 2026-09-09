"""Standard-library adapter for the upstream PaperBanana diagram CLI."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


PROBE = r'''
import importlib.util, json, os
from pathlib import Path
modules = ['google.genai', 'PIL', 'numpy', 'aiofiles', 'json_repair',
           'anthropic', 'openai', 'matplotlib', 'dotenv', 'yaml',
           'huggingface_hub', 'tqdm']
missing = []
for name in modules:
    try:
        if importlib.util.find_spec(name) is None:
            missing.append(name)
    except (ImportError, ModuleNotFoundError):
        missing.append(name)
key_present = any(os.environ.get(k, '').strip() for k in
                  ['OPENROUTER_API_KEY', 'GOOGLE_API_KEY'])
config_error = False
path = Path('configs/model_config.yaml')
if path.exists() and 'yaml' not in missing:
    try:
        import yaml
        conf = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
        keys = conf.get('api_keys', {}) or {}
        key_present = key_present or any(str(keys.get(k) or '').strip()
                    for k in ['google_api_key', 'openrouter_api_key'])
    except Exception:
        config_error = True
print(json.dumps({'missing_modules': missing, 'key_present': bool(key_present),
                  'config_error': config_error}))
'''


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', required=True, type=Path)
    p.add_argument('--python', type=Path, dest='interpreter')
    p.add_argument('--check', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--content-file', type=Path)
    p.add_argument('--caption')
    p.add_argument('--output', type=Path)
    p.add_argument('--num-candidates', type=int, default=1)
    p.add_argument('--max-critic-rounds', type=int, choices=range(4), default=3)
    p.add_argument('--aspect-ratio', choices=['21:9', '16:9', '3:2'], default='16:9')
    p.add_argument('--retrieval-setting', choices=['auto', 'random', 'none'], default='auto')
    p.add_argument('--main-model-name')
    p.add_argument('--image-gen-model-name')
    return p


def paths(args):
    repo = args.repo.resolve()
    if not (repo / 'skill' / 'run.py').is_file():
        raise ValueError('Missing upstream skill/run.py; follow references/runtime.md.')
    interpreter = args.interpreter
    if interpreter is None:
        interpreter = repo / '.venv' / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
    interpreter = interpreter.absolute()
    if not interpreter.is_file():
        raise ValueError('Missing project Python; create its venv or pass --python PATH.')
    return repo, interpreter


def preflight(repo, interpreter):
    proc = subprocess.run([str(interpreter), '-c', PROBE], cwd=repo,
                          capture_output=True, text=True, timeout=30)
    if proc.returncode:
        raise ValueError('Environment probe failed; check the project Python environment.')
    report = json.loads(proc.stdout)
    print(json.dumps(report, ensure_ascii=False))
    return not report['missing_modules'] and report['key_present'] and not report['config_error']


def build_command(args, repo, interpreter):
    if not args.content_file or not args.caption or not args.caption.strip() or not args.output:
        raise ValueError('--content-file, --caption and --output are required for generation.')
    content = args.content_file.resolve()
    if not content.is_file() or not content.read_text(encoding='utf-8-sig').strip():
        raise ValueError('Content must be a nonempty UTF-8 text file.')
    output = args.output.resolve()
    if output.suffix.lower() != '.png':
        raise ValueError('Output must have a .png suffix.')
    if args.num_candidates < 1:
        raise ValueError('--num-candidates must be positive.')
    expected = [output] if args.num_candidates == 1 else [
        output.with_name(f'{output.stem}_{i}{output.suffix}') for i in range(args.num_candidates)]
    if any(p.exists() for p in expected):
        raise ValueError('Output already exists; choose a fresh output path.')
    command = [str(interpreter), str(repo / 'skill' / 'run.py'),
               '--content-file', str(content), '--caption', args.caption,
               '--task', 'diagram', '--output', str(output), '--exp-mode', 'demo_full',
               '--num-candidates', str(args.num_candidates),
               '--max-critic-rounds', str(args.max_critic_rounds),
               '--aspect-ratio', args.aspect_ratio, '--retrieval-setting', args.retrieval_setting]
    for flag in ['main_model_name', 'image_gen_model_name']:
        if getattr(args, flag):
            command.extend(['--' + flag.replace('_', '-'), getattr(args, flag)])
    return command, expected


def execute(command, expected, repo):
    expected[0].parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(command, cwd=repo)  # argument array; never shell=True
    if proc.returncode:
        return proc.returncode
    invalid = []
    for path in expected:
        if not path.is_file():
            invalid.append(str(path))
            continue
        with path.open('rb') as image:
            if image.read(8) != b'\x89PNG\r\n\x1a\n' or path.stat().st_size <= 33:
                invalid.append(str(path))
    if invalid:
        print(json.dumps({'error': 'Missing or invalid PNG outputs', 'paths': invalid}), file=sys.stderr)
        return 3
    print(json.dumps({'files_written': [str(p) for p in expected],
                      'visual_review': 'required; PNG signature only checked'}, ensure_ascii=False))
    return 0


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    try:
        repo, interpreter = paths(args)
        if args.check:
            return 0 if preflight(repo, interpreter) else 2
        command, expected = build_command(args, repo, interpreter)
        if args.dry_run:
            print(json.dumps({'dry_run': True, 'argv': command,
                              'expected_outputs': [str(x) for x in expected]}, ensure_ascii=False))
            return 0
        if not preflight(repo, interpreter):
            return 2
        return execute(command, expected, repo)
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
