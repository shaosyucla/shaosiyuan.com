"""Summarise the Squarespace ?format=json-pretty dumps in ..\original."""
import json, re, os

ORIG = os.path.join(os.path.dirname(__file__), '..', 'original')
PAGES = ['home', 'about', 'towards-ornithopter', 'jumping-vehicle',
         'moments-mechanical', 'course-projects', 'life', 'contact']
VID = re.compile(r'(youtube\.com/[^"&\s\\]+|youtu\.be/[^"&\s\\]+|vimeo\.com/[^"&\s\\]+|video\.squarespace-cdn[^"\s\\]+)')

for p in PAGES:
    d = json.load(open(os.path.join(ORIG, p + '.json'), encoding='utf-8'))
    coll = d.get('collection', {})
    items = d.get('items')
    mc = d.get('mainContent', '')
    print('==', p, '| typeName', coll.get('typeName'), '| items', len(items) if items else None,
          '| mainContent', len(mc) if isinstance(mc, str) else type(mc))
    if items:
        for it in items:
            body = it.get('body', '') or ''
            vids = set(VID.findall(body))
            print('   ', it.get('urlId'), '|', it.get('title'), '| body', len(body),
                  '| vids', vids or '', '| asset', (it.get('assetUrl') or '')[-45:])
    elif isinstance(mc, str):
        print('    vids', set(VID.findall(mc)) or '')
