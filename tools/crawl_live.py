"""Breadth-first crawl of www.shaosiyuan.com following every internal link (static HTML),
starting from sitemap.xml. Prints every page found that is not in the sitemap.
Result list: ..\\original\\crawl_paths.txt"""
import os, re, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
ORIG = os.path.join(ROOT, 'original')
HOST = 'https://www.shaosiyuan.com'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36'
SKIP = re.compile(r'^/(s/|cart|api/|static/|universal/|config|account|commerce|search)')


def norm(href, base):
    href = (href or '').strip().replace('\\', '/')
    if not href or href.startswith(('mailto:', 'tel:', 'javascript:', '#', 'data:')):
        return None
    u = urllib.parse.urlparse(urllib.parse.urljoin(base, href))
    if u.netloc not in ('www.shaosiyuan.com', 'shaosiyuan.com'):
        return None
    path = u.path.rstrip('/') or '/'
    if SKIP.match(path) or re.search(r'\.(jpg|jpeg|png|gif|pdf|zip|css|js|ico|svg|xml)$', path, re.I):
        return None
    q = urllib.parse.parse_qs(u.query)
    if 'offset' in q:
        path += '?offset=' + q['offset'][0]
    return path


def fetch(path):
    try:
        req = urllib.request.Request(HOST + path, headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            return path, r.status, r.read().decode('utf-8', 'replace')
    except Exception as e:  # noqa: BLE001
        return path, getattr(e, 'code', 'ERR'), ''


def main():
    sitemap = {l.strip() or '/' for l in open(os.path.join(ORIG, 'sitemap_paths.txt')) if l.strip()}
    sitemap.add('/')
    seen, frontier, status = set(sitemap), list(sitemap), {}
    while frontier:
        with ThreadPoolExecutor(8) as ex:
            results = list(ex.map(fetch, frontier))
        frontier = []
        for path, code, html in results:
            status[path] = code
            for href in re.findall(r'href="([^"]+)"', html):
                p = norm(href, HOST + path.split('?')[0])
                if p and p not in seen:
                    seen.add(p)
                    frontier.append(p)
    extra = sorted(p for p in seen if p not in sitemap)
    open(os.path.join(ORIG, 'crawl_paths.txt'), 'w').write('\n'.join(sorted(seen)) + '\n')
    print('pages reached: %d (sitemap %d)' % (len(seen), len(sitemap)))
    print('not in sitemap:')
    for p in extra:
        print('  %s  [%s]' % (p, status.get(p)))
    bad = sorted((p, c) for p, c in status.items() if c != 200)
    print('non-200:', bad)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
