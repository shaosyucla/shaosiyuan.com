"""Print the block structure of the plain pages (about, life, contact) and one blog post body."""
import json, re, os, html

ORIG = os.path.join(os.path.dirname(__file__), '..', 'original')


def blocks(s):
    """List sqs-block types and a short text/attr preview in document order."""
    for m in re.finditer(r'<div class="sqs-block ([a-z0-9-]+)-block[^"]*"([^>]*)>', s):
        kind = m.group(1)
        tail = s[m.end():m.end() + 1500]
        txt = re.sub(r'<[^>]+>', ' ', tail)
        txt = re.sub(r'\s+', ' ', html.unescape(txt)).strip()[:90]
        img = re.search(r'data-src="([^"]+)"', tail)
        print('   ', kind, '|', txt, '|', img.group(1)[-50:] if img else '')


for p in ['about', 'life', 'contact']:
    s = open(os.path.join(ORIG, p + '.html'), encoding='utf-8').read()
    main = s[s.find('<main'):s.find('</main>')]
    print('==', p, len(main), 'sections', main.count('<section'))
    blocks(main)

d = json.load(open(os.path.join(ORIG, 'jumping-vehicle.json'), encoding='utf-8'))
it = d['items'][0]
print('== post', it['urlId'], list(it.keys()))
blocks(it['body'])
print(it['body'][:3000])
