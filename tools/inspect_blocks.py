"""Count Squarespace block kinds (data-definition-name) across all posts and plain pages."""
import json, re, os, collections

ORIG = os.path.join(os.path.dirname(__file__), '..', 'original')
DEF = re.compile(r'data-definition-name="([^"]+)"')
cnt = collections.Counter()
imgs = set()

for p in ['towards-ornithopter', 'jumping-vehicle', 'moments-mechanical', 'course-projects']:
    d = json.load(open(os.path.join(ORIG, p + '.json'), encoding='utf-8'))
    for it in d['items']:
        cnt.update(DEF.findall(it['body']))
        imgs.update(re.findall(r'data-src="(https://images[^"]+)"', it['body']))
for p in ['index', 'about', 'life', 'contact']:
    s = open(os.path.join(ORIG, p + '.html'), encoding='utf-8').read()
    main = s[s.find('<main'):s.find('</main>')]
    c = collections.Counter(DEF.findall(main))
    print(p, dict(c))
    imgs.update(re.findall(r'data-src="(https://images[^"]+)"', main))
print('posts', dict(cnt))
print('unique images', len(imgs))
