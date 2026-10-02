"""compare/orig_<n>.png + compare/new_<n>.png -> compare/sbs_<n>.png (live left, rebuild right)."""
import os, sys
from PIL import Image, ImageDraw

CMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'compare')
for n in sys.argv[1:]:
    a = Image.open(os.path.join(CMP, 'orig_%s.png' % n)).convert('RGB')
    b = Image.open(os.path.join(CMP, 'new_%s.png' % n)).convert('RGB')
    h = max(a.height, b.height)
    out = Image.new('RGB', (a.width + b.width + 20, h + 40), 'red')
    out.paste(a, (0, 40))
    out.paste(b, (a.width + 20, 40))
    d = ImageDraw.Draw(out)
    d.rectangle([0, 0, out.width, 39], fill='white')
    d.text((10, 10), 'LIVE (Squarespace)', fill='black')
    d.text((a.width + 30, 10), 'REBUILD (local)', fill='black')
    out = out.resize((out.width // 2, out.height // 2), Image.LANCZOS)
    p = os.path.join(CMP, 'sbs_%s.png' % n)
    out.save(p)
    print(p)
