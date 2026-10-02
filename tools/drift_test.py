"""Vertical drift test: the same text on the live site and the copy should sit at the same height.

    python drift_test.py [new-base] [--device "iPhone 17 Pro" | --width 1280] [--skip-live] [p=/path ...]

For every page (default: all pages of the click-through), every heading and paragraph in the main content is
matched by its text on both sites. Per page it prints the page-height difference, the largest drift and the
first element whose drift exceeds 6px (where a spacing difference starts). Live results are cached in
../compare/drift/live_<setup>.json so --skip-live reruns only the copy.
Positions are the element's text lines (Range over each text node), so padding and margin choices do not count.
"spacing" removes line-wrap differences (font metrics): it compares the gap between consecutive texts.
Output: ../compare/drift/report_<setup>.txt
"""
import asyncio, json, os, re, sys
from playwright.async_api import async_playwright
from clickthrough import page_paths

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'compare', 'drift')
LIVE = 'https://www.shaosiyuan.com'

JS = r"""(live) => {
  const main = live ? (document.querySelector('#page') || document.querySelector('main') || document.body) : document.querySelector('main');
  const out = [];
  const seen = new Set();
  for (const e of main.querySelectorAll('h1, h2, h3, h4, p, blockquote, figcaption')) {
    if (!e.getClientRects().length) continue;
    const t = e.innerText.replace(/\s+/g, ' ').trim().slice(0, 40);
    if (t.length < 4 || seen.has(t)) continue;
    seen.add(t);
    // text lines only (no element boxes, so padding vs margin and inner padding do not count)
    let top = Infinity, bottom = -Infinity;
    const w = document.createTreeWalker(e, NodeFilter.SHOW_TEXT);
    for (let n = w.nextNode(); n; n = w.nextNode()) {
      if (!n.data.trim()) continue;
      const r = document.createRange(); r.selectNodeContents(n);
      for (const b of r.getClientRects()) { if (b.height) { top = Math.min(top, b.top); bottom = Math.max(bottom, b.bottom); } }
    }
    if (top === Infinity) continue;
    out.push([t, Math.round(top + scrollY), Math.round(bottom - top)]);
  }
  const f = document.querySelector(live ? 'footer' : '.site-footer');
  return {items: out, height: document.documentElement.scrollHeight,
          footer: f ? Math.round(f.getBoundingClientRect().top + scrollY) : null};
}"""


async def measure(ctx, base, path, sem):
    async with sem:
        p = await ctx.new_page()
        try:
            await p.goto(base + path, wait_until='load', timeout=60000)
            await p.evaluate('async () => { for (let y=0;y<document.body.scrollHeight;y+=600){scrollTo(0,y);await new Promise(r=>setTimeout(r,50));} scrollTo(0,0); }')
            await p.wait_for_timeout(1200)
            r = await p.evaluate(JS, base == LIVE)
        except Exception as e:  # noqa: BLE001
            r = {'error': str(e).split('\n')[0][:120]}
        await p.close()
        return path, r


def compare(live, new):
    if 'error' in live or 'error' in new:
        return None
    key = lambda t: re.sub(r'[^ -~]', '?', t)     # the live site has broken characters in some titles
    pos = {key(i[0]): i for i in new['items']}
    pairs = [(l, pos[key(l[0])]) for l in live['items'] if key(l[0]) in pos]
    drifts = [(l[0], n[1] - l[1]) for l, n in pairs]
    first = next(((t, d) for t, d in drifts if abs(d) > 6), None)
    worst = max(drifts, key=lambda x: abs(x[1]), default=(None, 0))
    # spacing error between consecutive texts = change in drift minus the height change of the text above
    # (a paragraph that wraps to one more or one fewer line is a font difference, not a spacing difference)
    gaps = [(n[0], (n[1] - l[1]) - (pn[1] - pl[1]) - (pn[2] - pl[2]))
            for (pl, pn), (l, n) in zip(pairs, pairs[1:]) if n[1] > pn[1]]
    gap = max(gaps, key=lambda x: abs(x[1]), default=(None, 0))
    return {'dh': new['height'] - live['height'], 'matched': len(drifts), 'of': len(live['items']),
            'worst': worst, 'first': first, 'gap': gap,
            'footer': (new['footer'] - live['footer']) if live['footer'] and new['footer'] else None}


async def main():
    a = sys.argv[1:]
    dev = a[a.index('--device') + 1] if '--device' in a else None
    width = int(a[a.index('--width') + 1]) if '--width' in a else None
    skip = {a[a.index(k) + 1] for k in ('--device', '--width') if k in a}
    pos = [x for x in a if not x.startswith('--') and not x.startswith('p=') and x not in skip]
    new_base = (pos[0] if pos else 'http://127.0.0.1:8792').rstrip('/')
    paths = [x[2:] for x in a if x.startswith('p=')] or page_paths()
    setup = re.sub(r'\W+', '', dev) if dev else 'w%d' % (width or 1280)
    os.makedirs(OUT, exist_ok=True)
    cache = os.path.join(OUT, 'live_%s.json' % setup)
    live = json.load(open(cache, encoding='utf-8')) if '--skip-live' in a and os.path.exists(cache) else {}
    async with async_playwright() as pw:
        b = await (pw.webkit.launch() if dev and 'iP' in dev else pw.chromium.launch(channel='chrome'))
        if dev:
            o = dict(pw.devices[dev]); o.pop('default_browser_type', None); o['device_scale_factor'] = 1
        else:
            o = {'viewport': {'width': width or 1280, 'height': 800}}
        sem = asyncio.Semaphore(4)
        todo = [p for p in paths if p not in live]
        if todo:
            ctx = await b.new_context(**o)
            live.update(dict(await asyncio.gather(*(measure(ctx, LIVE, p, sem) for p in todo))))
            await ctx.close()
            json.dump(live, open(cache, 'w', encoding='utf-8'))
        ctx = await b.new_context(**o)
        new = dict(await asyncio.gather(*(measure(ctx, new_base, p, sem) for p in paths)))
        await b.close()
    lines, clean, spaced = [], 0, 0
    for p in paths:
        c = compare(live[p], new[p])
        if c is None:
            lines.append('%-48s ERROR %s %s' % (p, live[p].get('error'), new[p].get('error')))
            continue
        ok = abs(c['worst'][1]) <= 6 and abs(c['dh']) <= 6
        clean += ok
        spaced += abs(c['gap'][1]) <= 6
        if not ok:
            first = '%+d at "%s"' % (c['first'][1], c['first'][0]) if c['first'] else '-'
            gap = '%+d before "%s"' % (c['gap'][1], c['gap'][0]) if abs(c['gap'][1]) > 6 else 'ok'
            lines.append('%-48s height %+5d  footer %+5s  worst %+5d  first >6px: %s  spacing: %s  (%d/%d matched)' % (
                p, c['dh'], c['footer'], c['worst'][1], first, gap, c['matched'], c['of']))
    lines.insert(0, '%s: pages within 6px everywhere: %d / %d; pages whose spacing between texts is within 6px '
                    '(line-wrap differences removed): %d / %d' % (setup, clean, len(paths), spaced, len(paths)))
    open(os.path.join(OUT, 'report_%s.txt' % setup), 'w', encoding='utf-8').write('\n'.join(lines))
    print('\n'.join(lines))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(main())
