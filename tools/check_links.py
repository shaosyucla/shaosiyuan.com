"""Check every local href/src in ..\\site\\**\\*.html points to an existing file. Lists external hosts too."""
import os, re, collections, urllib.parse

SITE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'site')
missing = collections.defaultdict(set)
external = collections.Counter()
pages = 0
for dirpath, _, files in os.walk(SITE):
    for f in files:
        if not f.endswith('.html'):
            continue
        pages += 1
        path = os.path.join(dirpath, f)
        s = open(path, encoding='utf-8').read()
        for url in re.findall(r'\b(?:href|src)="([^"]+)"', s):
            if url.startswith(('http:', 'https:', 'mailto:', 'tel:', '#', 'data:')):
                external[urllib.parse.urlparse(url).netloc] += 1
                continue
            rel = urllib.parse.unquote(url.split('#')[0])
            base = SITE if rel.startswith('/') else dirpath   # root paths (404.html) resolve from the site root
            target = os.path.normpath(os.path.join(base, rel.lstrip('/')))
            # addresses without .html are served like GitHub Pages: /about -> about.html or about/index.html
            found = (os.path.isfile(target) or os.path.isfile(target + '.html')
                     or os.path.isfile(os.path.join(target, 'index.html')))
            if not found:
                missing[url].add(os.path.relpath(path, SITE))
print('pages checked:', pages)
print('missing local targets:', len(missing))
for u, where in sorted(missing.items()):
    print('  ', u, '<-', ', '.join(sorted(where))[:200])
print('external hosts:', dict(external.most_common()))
