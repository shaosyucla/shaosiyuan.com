"""Old-address test: every address of the live Squarespace site must open the same page on the new host.

    python url_test.py https://shaosyucla.github.io/shaosiyuan.com
    python url_test.py https://www.shaosiyuan.com          (after the DNS switch: compares against the saved live titles)

For each address found by tools/crawl_live.py (plus the same address with a trailing slash, and every
/s/<file> link on the live pages) it fetches the live page and the new page and compares HTTP status
and <title>. Files (/s/...) are compared by status and content type.
"""
import html, json, os, re, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
ORIG = os.path.join(ROOT, 'original')
LIVE = 'https://www.shaosiyuan.com'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36'
TITLES = os.path.join(ORIG, 'live_titles.json')


def fetch(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read(200000)
            ctype = r.headers.get('Content-Type', '')
            return r.status, ctype, body, r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get('Content-Type', ''), e.read(200000), url
    except Exception as e:  # noqa: BLE001
        return 'ERR ' + str(e)[:60], '', b'', url


def title_of(body):
    m = re.search(rb'<title>(.*?)</title>', body, re.S)
    t = html.unescape(m.group(1).decode('utf-8', 'replace')).strip() if m else ''
    return re.sub(r'\s+', ' ', t)


def norm_title(t):
    return re.sub(r'[\s—–|—–-]+', ' ', t).strip().lower()


def addresses():
    paths = [p.strip() or '/' for p in open(os.path.join(ORIG, 'crawl_paths.txt')) if p.strip()]
    paths = [p for p in paths if p != '/success' and '?offset=' not in p]
    out = list(paths)
    out += [p + '/' for p in paths if p != '/']                      # trailing-slash form
    files = set()
    for f in os.listdir(ORIG):
        if f.endswith(('.html', '.json')):
            for m in re.finditer(r'(?:https://www\.shaosiyuan\.com)?(/s/[^"\'\s<>\\?#]+)', open(os.path.join(ORIG, f), encoding='utf-8', errors='replace').read()):
                files.add(m.group(1))
    out += sorted(files)
    return out


def main():
    new = sys.argv[1].rstrip('/')
    addrs = addresses()
    live_titles = json.load(open(TITLES, encoding='utf-8')) if os.path.exists(TITLES) else {}

    def one(path):
        if path.startswith('/s/'):
            ls, lc, _, _ = fetch(LIVE + path)
            ns, nc, _, _ = fetch(new + path)
            ok = (ns == 200) == (ls == 200) and (ns != 200 or nc.split(';')[0] == lc.split(';')[0])
            return path, ls, ns, lc.split(';')[0], nc.split(';')[0], ok
        if path in live_titles:
            ls, lt = live_titles[path]
        else:
            ls, _, lb, _ = fetch(LIVE + path)
            lt = title_of(lb)
        ns, _, nb, nurl = fetch(new + path)
        nt = title_of(nb)
        if nt.startswith('Redirecting'):                              # /home -> home page
            m = re.search(rb'url=([^"]+)"', nb)
            ns, _, nb, _ = fetch(urllib.parse.urljoin(nurl, m.group(1).decode())) if m else (ns, '', nb, '')
            nt = title_of(nb)
        ok = ns == 200 and ls == 200 and norm_title(nt) == norm_title(lt)
        return path, ls, ns, lt, nt, ok

    with ThreadPoolExecutor(8) as ex:
        rows = list(ex.map(one, addrs))
    if not live_titles:
        json.dump({p: [ls, lt] for p, ls, ns, lt, nt, ok in rows if not p.startswith('/s/')}, open(TITLES, 'w', encoding='utf-8'), indent=0)
    bad = [r for r in rows if not r[5]]
    pages = [r for r in rows if not r[0].startswith('/s/')]
    files = [r for r in rows if r[0].startswith('/s/')]
    print('addresses tested: %d (%d page addresses incl. trailing-slash forms, %d file links)' % (len(rows), len(pages), len(files)))
    print('same page on the new host: %d / %d' % (len(rows) - len(bad), len(rows)))
    for p, ls, ns, lt, nt, ok in bad:
        print('  DIFF %-60s live %s "%s" | new %s "%s"' % (p[:60], ls, str(lt)[:40], ns, str(nt)[:40]))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
