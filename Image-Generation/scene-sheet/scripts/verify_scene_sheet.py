"""Verify source integrity, six-cell geometry and exported image pixels, not likeness."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


def check(condition, message):
    if not condition:
        raise ValueError(message)


def verify(output, manifest_path):
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    keys = ['B', 'A', 'C', 'detail_object', 'detail_feature', 'detail_material']
    check(manifest['layout'] == 'scene-sheet-3x2', 'Wrong layout')
    check([a['key'] for a in manifest['assets']] == keys, 'Wrong six-asset order')
    check(hashlib.sha256(Path(output).read_bytes()).hexdigest() == manifest['output_sha256'],
          'Export changed')
    g = manifest['geometry']
    w, top, bottom = g['cell_width'], g['view_height'], g['detail_height']
    pad, gap, label = g['padding'], g['gap'], g['label_height']
    expected_size = [2*pad+3*w+2*gap, 2*pad+top+bottom+2*label+gap]
    with Image.open(output) as source:
        sheet = source.convert('RGB')
    check(list(sheet.size) == expected_size == manifest['size'], 'Wrong canvas size')
    for i, record in enumerate(manifest['assets']):
        path = Path(record['source'])
        check(hashlib.sha256(path.read_bytes()).hexdigest() == record['source_sha256'],
              f'Source changed: {path}')
        h = top if i < 3 else bottom
        x = pad+(i % 3)*(w+gap)
        y = pad if i < 3 else pad+top+label+gap
        check(record['cell'] == [x,y,w,h], 'Wrong cell placement')
        left, upper, iw, ih = record['image_box']
        check(iw > 0 and ih > 0 and x <= left and y <= upper and
              left+iw <= x+w and upper+ih <= y+h, 'Image outside cell')
        sw, sh = record['source_size']
        scale = min(w/sw, h/sh)
        check(abs(iw-sw*scale) <= 1 and abs(ih-sh*scale) <= 1, 'Stretched image')
        check(left == x+(w-iw)//2 and upper == y+(h-ih)//2, 'Image not centered')
        pixels = sheet.crop((left,upper,left+iw,upper+ih)).tobytes()
        check(hashlib.sha256(pixels).hexdigest() == record['tile_sha256'], 'Tile pixels changed')
    print('PASS: six assets, source hashes, layout, aspect ratios and exported pixels. '
          'Visual scene consistency still requires inspection.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    verify(args.output, args.manifest)
