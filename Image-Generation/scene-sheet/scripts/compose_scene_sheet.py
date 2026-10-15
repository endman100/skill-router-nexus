"""Compose six accepted source assets; image generation stays in ImageGen."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

KEYS = ('B', 'A', 'C', 'detail_object', 'detail_feature', 'detail_material')
LABELS = ('B | LEFT CORNER', 'A | REVERSE', 'C | RIGHT CORNER',
          'OBJECT DETAIL', 'SCENE FEATURE', 'MATERIAL DETAIL')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def integer(config, key, default):
    value = config.get(key, default)
    if type(value) is not int or value < 64:
        raise ValueError(f'{key} must be an integer >= 64')
    return value


def font_for(config, directory, size):
    requested = config.get('font')
    candidates = ([str(directory / requested)] if requested else []) + [
        'C:/Windows/Fonts/msjh.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/System/Library/Fonts/PingFang.ttc', 'DejaVuSans.ttf']
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    if any(not label.isascii() for label in config.get('labels', {}).values()):
        raise ValueError('Set config.font to a font that supports your labels')
    return ImageFont.load_default()


def compose(config_path, output):
    config_path, output = Path(config_path).resolve(), Path(output).resolve()
    config = json.loads(config_path.read_text(encoding='utf-8-sig'))
    manifest_path = output.with_suffix('.manifest.json')
    if output.suffix.lower() != '.png':
        raise ValueError('Output must be a PNG')
    if output.exists() or manifest_path.exists():
        raise FileExistsError('Choose a new output filename; existing files are preserved')
    if set(config['assets']) != set(KEYS):
        raise ValueError(f'Provide exactly six assets: {KEYS}')
    images, paths = {}, {}
    for key in KEYS:
        path = (config_path.parent / config['assets'][key]).resolve()
        paths[key] = path
        with Image.open(path) as source:
            rgba = ImageOps.exif_transpose(source).convert('RGBA')
            white = Image.new('RGBA', rgba.size, 'white')
            images[key] = Image.alpha_composite(white, rgba).convert('RGB')
    w = integer(config, 'cell_width', 800)
    base = images['B']
    top = integer(config, 'view_height', round(w * base.height / base.width))
    bottom = integer(config, 'detail_height', max(64, top // 2))
    pad, gap, label_h = 24, 16, 44
    canvas = Image.new('RGB', (2*pad + 3*w + 2*gap,
                              2*pad + top + bottom + 2*label_h + gap), '#fffdfb')
    draw = ImageDraw.Draw(canvas)
    records = []
    for index, (key, default_label) in enumerate(zip(KEYS, LABELS)):
        h = top if index < 3 else bottom
        x = pad + (index % 3) * (w + gap)
        y = pad if index < 3 else pad + top + label_h + gap
        tile = ImageOps.contain(images[key], (w, h), Image.Resampling.LANCZOS)
        left, upper = x + (w-tile.width)//2, y + (h-tile.height)//2
        canvas.paste(tile, (left, upper))
        label = config.get('labels', {}).get(key, default_label)
        size = max(12, w//40)
        font = font_for(config, config_path.parent, size)
        while draw.textlength(label, font=font) > w-20 and size > 10:
            size -= 1
            font = font_for(config, config_path.parent, size)
        if draw.textlength(label, font=font) > w-20:
            raise ValueError(f'Shorten label for {key}')
        draw.text((x+w-10, y+h+label_h//2), label, fill='#75645f', font=font, anchor='rm')
        records.append({'key': key, 'source': str(paths[key]),
                        'source_sha256': digest(paths[key]),
                        'source_size': list(images[key].size), 'cell': [x,y,w,h],
                        'image_box': [left, upper, tile.width, tile.height],
                        'tile_sha256': hashlib.sha256(tile.tobytes()).hexdigest(),
                        'label': label})
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)
    manifest = {'layout': 'scene-sheet-3x2', 'size': list(canvas.size),
                'geometry': {'cell_width': w, 'view_height': top, 'detail_height': bottom,
                             'padding': pad, 'gap': gap, 'label_height': label_h},
                'output_sha256': digest(output), 'assets': records}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(output), 'manifest': str(manifest_path),
                      'size': list(canvas.size)}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    compose(args.config, args.output)
