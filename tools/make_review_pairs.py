"""Side-by-side review images from the click-through screenshots.

compare/clickthrough/shots/{live,new}/<page>.jpg  ->  compare/review/<page>__<k>.jpg
Left half = live Squarespace, right half = rebuild, both scaled to 640 px wide, cut into
1500 px tall slices (same vertical slice of both pages). Writes compare/review/manifest.json.
"""
import json, os, glob
from PIL import Image, ImageDraw

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SHOTS = os.path.join(ROOT, 'compare', 'clickthrough', 'shots')
OUT = os.path.join(ROOT, 'compare', 'review')
W, SLICE, GAP, BAR = 640, 1500, 16, 28
Image.MAX_IMAGE_PIXELS = None


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in glob.glob(os.path.join(OUT, '*.jpg')):
        os.remove(f)
    manifest = []
    for live_path in sorted(glob.glob(os.path.join(SHOTS, 'live', '*.jpg'))):
        name = os.path.splitext(os.path.basename(live_path))[0]
        new_path = os.path.join(SHOTS, 'new', name + '.jpg')
        if not os.path.exists(new_path):
            continue
        a, b = Image.open(live_path).convert('RGB'), Image.open(new_path).convert('RGB')
        a = a.resize((W, round(a.height * W / a.width)), Image.LANCZOS)
        b = b.resize((W, round(b.height * W / b.width)), Image.LANCZOS)
        h = max(a.height, b.height)
        files = []
        for k, top in enumerate(range(0, h, SLICE)):
            out = Image.new('RGB', (2 * W + GAP, SLICE + BAR), (230, 0, 0))
            d = ImageDraw.Draw(out)
            d.rectangle([0, 0, out.width, BAR - 1], fill='white')
            d.text((8, 8), 'LIVE (Squarespace)  %s  slice %d' % (name, k + 1), fill='black')
            d.text((W + GAP + 8, 8), 'REBUILD  %s  slice %d' % (name, k + 1), fill='black')
            for x, im in ((0, a), (W + GAP, b)):
                piece = im.crop((0, top, W, min(top + SLICE, im.height))) if top < im.height else None
                if piece:
                    out.paste(piece, (x, BAR))
            used = min(SLICE, h - top) + BAR
            p = os.path.join(OUT, '%s__%d.jpg' % (name, k + 1))
            out.crop((0, 0, out.width, used)).save(p, quality=80)
            files.append(p)
        manifest.append({'page': name, 'liveHeight': a.height * 2, 'newHeight': b.height * 2, 'files': files})
    json.dump(manifest, open(os.path.join(OUT, 'manifest.json'), 'w'), indent=1)
    print('pages', len(manifest), 'images', sum(len(m['files']) for m in manifest))


if __name__ == '__main__':
    main()
