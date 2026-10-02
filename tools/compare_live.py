"""Compare every live page (rendered by headless Chrome) with the rebuilt page.

    python compare_live.py dump      # render all live URLs into ..\\compare\\dom\\*.html (parallel)
    python compare_live.py report    # compare text / links / images / videos page by page

Per page it reports: words only on one side, links only on one side, images only on one side,
videos only on one side. Header and footer are excluded (checked once separately).
"""
import os, re, sys, subprocess, urllib.parse, collections
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SITE = os.path.join(ROOT, 'site')
DOM = os.path.join(ROOT, 'compare', 'dom')
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
HOST = 'https://www.shaosiyuan.com'


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def pages():
    """(live url, local file) for every sitemap URL plus page 2 of the ornithopter list."""
    out = []
    for p in open(os.path.join(ROOT, 'original', 'crawl_paths.txt')):   # sitemap + crawled links
        p = p.strip()
        parts = [x for x in p.split('/') if x]
        if p in ('/home', '/success') or '?offset=' in p:
            continue  # /home = alias of /; /success is password protected; offsets added below
        if len(parts) == 3 and parts[1] == 'category':
            local = '%s/category/%s.html' % (parts[0], slug(urllib.parse.unquote_plus(parts[2])))
        else:
            local = '/'.join(parts) + '.html' if parts else 'index.html'
        out.append((HOST + (p or '/'), local))
    out.append((HOST + '/towards-ornithopter?offset=1598506500235', 'towards-ornithopter/page-2.html'))
    return sorted(set(out))


def dom_path(local):
    return os.path.join(DOM, local.replace('/', '__'))


def dump():
    os.makedirs(DOM, exist_ok=True)

    def one(item):
        url, local = item
        if os.path.exists(dom_path(local)) and os.path.getsize(dom_path(local)) > 1000:
            return local, os.path.getsize(dom_path(local))
        r = subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--virtual-time-budget=10000',
                            '--window-size=1280,2000', '--dump-dom', url], capture_output=True, timeout=120)
        open(dom_path(local), 'wb').write(r.stdout)
        return local, len(r.stdout)
    with ThreadPoolExecutor(6) as ex:
        for local, n in ex.map(one, pages()):
            print('%7d %s' % (n, local))


# ------------------------------------------------------------------ extraction
def img_key(src):
    """Original file name without the squarespace id / our 6-char tag, lower case."""
    if not src:
        return None
    name = urllib.parse.unquote(urllib.parse.urlparse(src).path.rsplit('/', 1)[-1]).replace('+', ' ')
    stem, ext = os.path.splitext(name)
    stem = re.sub(r'-[A-Z0-9]{6}(-\d+)?$', '', stem)            # our tag
    stem = re.sub(r'[^A-Za-z0-9]+', '-', stem).strip('-').lower()
    return stem


def video_key(src):
    m = re.search(r'(?:youtube\.com(?:/|%2F)embed(?:/|%2F)|youtu\.be/|youtube-nocookie\.com/embed/)([\w-]{11})', src)
    if m:
        return 'yt:' + m.group(1)
    m = re.search(r'vimeo\.com/(?:video/)?(\d+)', src)
    if m:
        return 'vimeo:' + m.group(1)
    return None


def link_key(href, base_local):
    if not href or href.startswith(('javascript:', '#', 'mailto:')):
        return None
    href = href.replace('\\', '/')
    u = urllib.parse.urlparse(href)
    if u.netloc and u.netloc not in ('www.shaosiyuan.com', 'shaosiyuan.com', '127.0.0.1:8791'):
        return href.split('#')[0].rstrip('/')
    path = u.path
    if not u.netloc and not path.startswith('/'):   # relative link in the rebuild
        path = '/' + os.path.normpath(os.path.join(os.path.dirname(base_local), path)).replace('\\', '/')
    path = re.sub(r'\.html$', '', path).rstrip('/')
    path = re.sub(r'/index$', '', path)
    if path in ('', '/home'):
        path = '/'
    if path.startswith('/s/'):
        path = '/files/' + path[3:]
    if '/files/' in path or '/img/' in path:
        path = '/files/' + img_key(path) if '/files/' in path else path
    if u.query.startswith('offset='):
        path += '?page2'
    if path.endswith('/page-2'):
        path = path[:-7] + '?page2'
    return path


def extract(html, base_local, live):
    soup = BeautifulSoup(html, 'lxml')
    for t in soup(['script', 'style', 'noscript', 'template']):
        t.decompose()
    if live:
        for t in soup.select('header, footer, .header, #footer-sections, .item-pagination, .blog-item-comments'):
            t.decompose()
        main = soup.find('main') or soup.body
    else:
        main = soup.find('main')
        for t in main.select('.post-pagination, .list-pagination'):
            t.decompose()
    words = re.findall(r'\w+', main.get_text(' ').lower()) if main else []
    links = collections.Counter(k for a in main.find_all('a') if (k := link_key(a.get('href'), base_local)))
    imgs = collections.Counter(k for i in main.find_all('img')
                               if (k := img_key(i.get('data-src') or i.get('data-image') or i.get('src'))))
    vids = set()
    for el in main.find_all(['iframe', 'div']):
        for attr in ('src', 'data-html', 'data-src', 'data-embed'):
            v = el.get(attr)
            if v and (k := video_key(v)):
                vids.add(k)
    return collections.Counter(words), links, imgs, vids


def diff(a, b):
    return {k: a[k] - b[k] for k in a if a[k] > b[k]}


def report():
    total, clean = 0, 0
    lines = []
    for url, local in pages():
        total += 1
        lp = dom_path(local)
        if not os.path.exists(lp) or os.path.getsize(lp) < 1000:
            lines.append('%s: LIVE DUMP MISSING' % local)
            continue
        live = extract(open(lp, encoding='utf-8', errors='replace').read(), local, True)
        mine = extract(open(os.path.join(SITE, local.replace('/', os.sep)), encoding='utf-8').read(), local, False)
        out = []
        names = ['words', 'links', 'images']
        for i, n in enumerate(names):
            only_live, only_mine = diff(live[i], mine[i]), diff(mine[i], live[i])
            if n == 'words':   # ignore small wording noise ("Read More", dates)
                if sum(only_live.values()) + sum(only_mine.values()) <= 4:
                    continue
            if only_live:
                out.append('  %s only on live: %s' % (n, dict(list(only_live.items())[:12])))
            if only_mine:
                out.append('  %s only in rebuild: %s' % (n, dict(list(only_mine.items())[:12])))
        if live[3] != mine[3]:
            out.append('  videos only on live: %s | only in rebuild: %s' % (sorted(live[3] - mine[3]), sorted(mine[3] - live[3])))
        if out:
            lines.append(local)
            lines.extend(out)
        else:
            clean += 1
    print('\n'.join(lines))
    print('\npages compared: %d, identical content: %d' % (total, clean))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    {'dump': dump, 'report': report}[sys.argv[1]]()
