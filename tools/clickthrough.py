"""Automated click-through + screenshot test: live Squarespace site vs the rebuild.

    python clickthrough.py                                   # rebuild at http://127.0.0.1:8792 (tools/serve.py 8792)
    python clickthrough.py https://shaosyucla.github.io/shaosiyuan.com   # rebuild on GitHub Pages
    python clickthrough.py --skip-live <url>                 # reuse the live results from the last run

Runs headless Chrome (no window, no focus change). For both sites it
  1. opens every page found by tools/crawl_live.py, scrolls it (lazy images, fade-ins), takes a full-page
     screenshot at 1280x800, and records status, title, images, videos, links, console errors;
  2. runs the same clicks on both sites (menu, home tiles, video thumbnails, Older Posts, post arrows,
     Life gallery links, phone menu, 404 page, old addresses) and records where each click lands.
Output: ..\\compare\\clickthrough\\{results.json, report.html, shots\\live|new\\*.jpg}
"""
import asyncio
import html
import json
import os
import re
import sys
import urllib.parse

from playwright.async_api import async_playwright

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'compare', 'clickthrough')
LIVE = 'https://www.shaosiyuan.com'
CONCURRENCY = 5
VIEW = {'width': 1280, 'height': 800}
PHONE = {'width': 375, 'height': 812}


def page_paths():
    paths = []
    for p in open(os.path.join(ROOT, 'original', 'crawl_paths.txt')):
        p = p.strip()
        if not p or p == '/success':          # password page: left out on purpose
            continue
        if '?offset=' in p and p != '/towards-ornithopter?offset=1598506500235':
            continue                          # crawl artefact of the "Newer Posts" link
        paths.append(p)
    return sorted(set(paths))


def shot_name(path):
    if path == '/':
        return 'home'
    return re.sub(r'[^A-Za-z0-9_.+-]+', '_', urllib.parse.unquote(path.strip('/')).replace('/', '__'))


def norm_path(url, base):
    """Comparable path: no host, no .html, no trailing slash, '/home' -> '/', offset -> page-2."""
    u = urllib.parse.urlsplit(url)
    b = urllib.parse.urlsplit(base)
    if u.netloc.startswith('static1.squarespace.com') and u.path.lower().endswith('.pdf'):
        u = u._replace(netloc=b.netloc, path='/files/' + u.path.rsplit('/', 1)[-1])   # Squarespace file host
    elif u.netloc and u.netloc not in (b.netloc, 'www.shaosiyuan.com', 'shaosiyuan.com'):
        return url.split('#')[0]
    path = u.path
    if b.path and b.path != '/' and path.startswith(b.path):   # GitHub project-site prefix
        path = path[len(b.path.rstrip('/')):]
    path = urllib.parse.unquote(path)
    path = re.sub(r'\.html$', '', path).rstrip('/') or '/'
    path = re.sub(r'/index$', '', path) or '/'
    if path == '/home':
        path = '/'
    if path.startswith('/s/'):
        path = '/files/' + path[3:]
    if 'offset=' in u.query and 'reversePaginate' not in u.query:
        path += '/page-2'
    if path.startswith(('/files/', '/img/')):     # file names differ by an id tag; compare stems
        stem = os.path.splitext(path.rsplit('/', 1)[-1])[0]
        path = path.split('/')[1] + ':' + re.sub(r'-[A-Z0-9]{6}(-\d+)?$', '', stem).lower()
    return path


PAGE_FACTS_JS = r"""() => {
  const vis = e => !!(e.offsetParent || e.getClientRects().length) && getComputedStyle(e).visibility !== 'hidden';
  const main = document.querySelector('main') || document.body;
  const imgs = [...main.querySelectorAll('img')].filter(vis);
  const vids = main.querySelectorAll('.video-block, .video').length;
  const links = [...document.querySelectorAll('main a[href], footer a[href]')].filter(vis).map(a => a.href);
  const h1 = [...main.querySelectorAll('h1')].filter(vis).map(h => h.innerText.trim()).filter(Boolean);
  return {
    title: document.title, h1, links,
    images: imgs.length,
    imagesBroken: imgs.filter(i => i.complete && i.naturalWidth === 0 && (i.currentSrc || i.src)).map(i => i.currentSrc || i.src),
    videos: vids,
    height: document.documentElement.scrollHeight,
  };
}"""

SCROLL_JS = r"""async () => {
  const step = 600;
  for (let y = 0; y < document.documentElement.scrollHeight; y += step) {
    window.scrollTo(0, y); await new Promise(r => setTimeout(r, 120));
  }
  window.scrollTo(0, document.documentElement.scrollHeight);
  await new Promise(r => setTimeout(r, 600));
  window.scrollTo(0, 0);
  await new Promise(r => setTimeout(r, 400));
}"""


async def visit(browser, base, site, path, sem):
    async with sem:
        ctx = await browser.new_context(viewport=VIEW, timezone_id='America/Detroit')
        page = await ctx.new_page()
        errors = []
        page.on('console', lambda m: errors.append(m.text[:200]) if m.type == 'error' else None)
        page.on('pageerror', lambda e: errors.append(str(e)[:200]))
        rec = {'path': path}
        try:
            resp = await page.goto(base.rstrip('/') + path, wait_until='load', timeout=60000)
            await page.wait_for_timeout(1500)             # client-side redirects (old page-2 address)
            rec['status'] = resp.status if resp else None
            await page.evaluate(SCROLL_JS)
            try:
                await page.wait_for_load_state('networkidle', timeout=8000)
            except Exception:  # noqa: BLE001
                pass
            facts = await page.evaluate(PAGE_FACTS_JS)
            facts['links'] = sorted(set(norm_path(u, base) for u in facts['links']))
            rec.update(facts)
            rec['final'] = norm_path(page.url, base)
            shot = os.path.join(OUT, 'shots', site, shot_name(path) + '.jpg')
            await page.screenshot(path=shot, full_page=True, type='jpeg', quality=70)
        except Exception as e:  # noqa: BLE001
            rec['error'] = str(e)[:300]
        # third-party noise (fonts, maps, players) is not a page defect
        rec['consoleErrors'] = [e for e in errors if not re.search(r'youtube|vimeo|google|gstatic|doubleclick|favicon|status of 401|compute-pressure|font-size:0', e, re.I)]
        await ctx.close()
        print('  %-5s %-60s %s' % (site, path[:60], rec.get('status', rec.get('error', '')[:40])), flush=True)
        return rec


# ------------------------------------------------------------------ scripted clicks
async def click_and_report(page, base, locator, label, wait=2500):
    try:
        await locator.first.scroll_into_view_if_needed(timeout=5000)
        await locator.first.click(timeout=8000)
        await page.wait_for_timeout(wait)
        return {'click': label, 'landed': norm_path(page.url, base), 'title': await page.title()}
    except Exception as e:  # noqa: BLE001
        return {'click': label, 'landed': None, 'error': str(e).split('\n')[0][:160]}


async def scenarios(browser, base, site):
    is_live = site == 'live'
    res = []
    url = lambda p: base.rstrip('/') + p  # noqa: E731
    ctx = await browser.new_context(viewport=VIEW, timezone_id='America/Detroit')
    page = await ctx.new_page()

    # 1. top menu, every item, from the home page
    nav_sel = ('.header-display-desktop .header-nav-item a' if is_live else '.site-nav a') + ':visible'
    await page.goto(url('/'), wait_until='load')
    labels = [t.strip() for t in await page.locator(nav_sel).all_inner_texts()]
    for lab in labels:
        await page.goto(url('/'), wait_until='load')
        r = await click_and_report(page, base, page.locator(nav_sel).filter(has_text=re.compile(r'^\s*%s\s*$' % re.escape(lab))), 'menu: ' + lab)
        res.append(r)
    # site title
    await page.goto(url('/about'), wait_until='load')
    title_sel = ('.header-display-desktop .header-title a' if is_live else '.site-title') + ':visible'
    res.append(await click_and_report(page, base, page.locator(title_sel), 'site title (from About)'))

    # 2. home page: 4 images and 4 buttons
    for lab in ['Towards Ornithopter', 'Moment Mechanical', 'Jumping Vehicle', 'Course Projects']:
        await page.goto(url('/'), wait_until='load')
        btn = page.locator('a', has_text=re.compile('^\\s*%s\\s*$' % re.escape(lab))).filter(
            has_not=page.locator('nav *')).last
        res.append(await click_and_report(page, base, btn, 'home button: ' + lab))
    for i in range(4):
        await page.goto(url('/'), wait_until='load')
        img = page.locator('main a:has(img)').nth(i)
        res.append(await click_and_report(page, base, img, 'home image %d' % (i + 1)))

    # 3. video thumbnails: click, the player must appear
    for path in ['/jumping-vehicle/let-go', '/towards-ornithopter/final-tests', '/moments-mechanical/metronome']:
        await page.goto(url(path), wait_until='load')
        box = page.locator('.sqs-video-wrapper' if is_live else '.video').first
        rec = {'click': 'video on ' + path}
        try:
            await box.scroll_into_view_if_needed(timeout=8000)
            await page.wait_for_timeout(1200)
            had_iframe = await box.locator('iframe').count()
            await box.click(timeout=8000)
            await page.wait_for_timeout(4000)
            src = await box.locator('iframe').first.get_attribute('src', timeout=8000)
            m = re.search(r'(youtube\.com/embed/[\w-]{11}|vimeo\.com/video/\d+)', src or '')
            rec.update({'landed': m.group(1) if m else src, 'iframeBeforeClick': bool(had_iframe),
                        'autoplay': 'autoplay=1' in (src or '')})
            await box.screenshot(path=os.path.join(OUT, 'shots', site, 'video_' + shot_name(path) + '.jpg'),
                                 type='jpeg', quality=75)
        except Exception as e:  # noqa: BLE001
            rec.update({'landed': None, 'error': str(e).split('\n')[0][:160]})
        res.append(rec)

    # 4. Older / Newer Posts
    await page.goto(url('/towards-ornithopter'), wait_until='load')
    res.append(await click_and_report(page, base, page.locator('a', has_text=re.compile('Older Posts', re.I)), 'Older Posts'))
    res.append(await click_and_report(page, base, page.locator('a', has_text=re.compile('Newer Posts', re.I)), 'Newer Posts'))

    # 5. post arrows
    await page.goto(url('/jumping-vehicle/let-go'), wait_until='load')
    nxt = page.locator('.item-pagination-link--next' if is_live else '.post-pagination .next')
    res.append(await click_and_report(page, base, nxt, 'next-post arrow on Let Go'))
    prv = page.locator('.item-pagination-link--prev' if is_live else '.post-pagination .prev')
    res.append(await click_and_report(page, base, prv, 'previous-post arrow (back)'))

    # 6. Life gallery images with links + a Life Blog category label
    for key in ['improved-lifestyle', 'francois-xavier-bagnoud', 'introduction-to-password']:
        await page.goto(url('/life'), wait_until='load')
        res.append(await click_and_report(page, base, page.locator('a[href*="%s"]:has(img)' % key), 'Life gallery image -> ' + key))
    await page.goto(url('/life-blog'), wait_until='load')
    res.append(await click_and_report(page, base, page.locator('a', has_text=re.compile('^Music$')), 'Life Blog "Music" label'))
    await page.goto(url('/introduction-to-password'), wait_until='load')
    res.append(await click_and_report(page, base, page.locator('main a', has_text='Here'), 'password page "Here" link'))

    # 7. About: resume link
    await page.goto(url('/about'), wait_until='load')
    href = await page.locator('main a', has_text='resume').first.get_attribute('href')
    res.append({'click': 'About: resume link target', 'landed': norm_path(urllib.parse.urljoin(page.url, href), base)})
    await ctx.close()

    # 8. phone: menu button opens the menu, menu item navigates
    pctx = await browser.new_context(viewport=PHONE, is_mobile=True, has_touch=True, timezone_id='America/Detroit')
    p2 = await pctx.new_page()
    await p2.goto(url('/about'), wait_until='load')
    await p2.wait_for_timeout(1200)
    burger = p2.locator(('.header-burger-btn' if is_live else '.menu-toggle') + ':visible').first
    rec = {'click': 'phone: menu button, then "Contact"'}
    try:
        await burger.click(timeout=8000)
        await p2.wait_for_timeout(1500)
        await p2.screenshot(path=os.path.join(OUT, 'shots', site, 'phone_menu_open.jpg'), type='jpeg', quality=75)
        item = p2.locator(('.header-menu-nav-item a' if is_live else '.site-nav a') + ':visible', has_text=re.compile(r'^\s*Contact\s*$'))
        await item.first.click(timeout=8000)
        await p2.wait_for_timeout(2500)
        rec['landed'] = norm_path(p2.url, base)
        await p2.screenshot(path=os.path.join(OUT, 'shots', site, 'phone_contact.jpg'), type='jpeg', quality=75, full_page=True)
    except Exception as e:  # noqa: BLE001
        rec.update({'landed': None, 'error': str(e).split('\n')[0][:160]})
    res.append(rec)
    await pctx.close()

    # 9. missing page and old addresses
    c3 = await browser.new_context(viewport=VIEW)
    p3 = await c3.new_page()
    r = await p3.goto(url('/this-page-does-not-exist'), wait_until='load')
    body = await p3.locator('body').inner_text()
    res.append({'click': 'missing address /this-page-does-not-exist', 'landed': 'status %s' % (r.status if r else None),
                'title': 'custom 404 text' if 'nothing to see here' in body.lower() else 'generic 404'})
    for old in ['/home', '/towards-ornithopter?offset=1598506500235', '/course-projects/category/ME350',
                '/life-blog/category/Hiking', '/s/SiyuanShao_Resume_General_20221116.pdf']:
        try:
            r = await p3.goto(url(old), wait_until='load')
            await p3.wait_for_timeout(1500)
            res.append({'click': 'old address ' + old, 'landed': norm_path(p3.url, base),
                        'title': 'status %s' % (r.status if r else None)})
        except Exception as e:  # noqa: BLE001
            # a PDF triggers a download in headless Chrome; treat a download as "file served"
            res.append({'click': 'old address ' + old, 'landed': 'file' if 'Download' in str(e) else None,
                        'error': None if 'Download' in str(e) else str(e).split('\n')[0][:160]})
    await c3.close()
    return res


# ------------------------------------------------------------------ report
def compare(live_pages, new_pages, live_clicks, new_clicks):
    by = {p['path']: p for p in new_pages}
    rows = []
    for lp in live_pages:
        np_ = by.get(lp['path'], {})
        issues = []
        if np_.get('status') not in (200, 304):
            issues.append('status %s' % np_.get('status') or np_.get('error'))
        if lp.get('final') != np_.get('final'):
            issues.append('lands on %s (live %s)' % (np_.get('final'), lp.get('final')))
        if lp.get('images') != np_.get('images'):
            issues.append('images %s vs live %s' % (np_.get('images'), lp.get('images')))
        if lp.get('videos') != np_.get('videos'):
            issues.append('videos %s vs live %s' % (np_.get('videos'), lp.get('videos')))
        if np_.get('imagesBroken'):
            issues.append('broken images: %d' % len(np_['imagesBroken']))
        if np_.get('consoleErrors'):
            issues.append('console errors: %s' % np_['consoleErrors'][:2])
        ll, nl = set(lp.get('links', [])), set(np_.get('links', []))
        if ll - nl:
            issues.append('links only on live: %s' % sorted(ll - nl)[:6])
        if nl - ll:
            issues.append('links only in rebuild: %s' % sorted(nl - ll)[:6])
        rows.append({'path': lp['path'], 'live': lp, 'new': np_, 'issues': issues})
    clicks = []
    nc = {c['click']: c for c in new_clicks}
    for lc in live_clicks:
        n = nc.get(lc['click'], {})
        same = lc.get('landed') == n.get('landed') and not n.get('error')
        clicks.append({'click': lc['click'], 'live': lc, 'new': n, 'same': same})
    for c in new_clicks:   # clicks that exist only on one side
        if c['click'] not in {x['click'] for x in live_clicks}:
            clicks.append({'click': c['click'], 'live': {}, 'new': c, 'same': False})
    return rows, clicks


def write_report(rows, clicks, new_base):
    e = lambda s: html.escape(str(s))  # noqa: E731
    ok_pages = sum(1 for r in rows if not r['issues'])
    ok_clicks = sum(1 for c in clicks if c['same'])
    h = ['<!DOCTYPE html><meta charset="utf-8"><title>Click-through test</title>',
         '<style>body{font:14px system-ui;margin:24px;background:#fafafa}table{border-collapse:collapse;width:100%}'
         'td,th{border:1px solid #ddd;padding:4px 8px;vertical-align:top;text-align:left}.ok{color:#1a7f37}.bad{color:#c62828}'
         '.pair{display:flex;gap:12px;margin:8px 0 28px}.pair figure{margin:0;flex:1}.pair img{width:100%;border:1px solid #ccc}'
         'h2{margin-top:40px}code{font-size:12px}</style>',
         '<h1>Click-through test: live Squarespace vs rebuild</h1>',
         '<p>Rebuild tested at <code>%s</code>. Clicks giving the same result: <b>%d / %d</b>. '
         'Pages without differences: <b>%d / %d</b>.</p>' % (e(new_base), ok_clicks, len(clicks), ok_pages, len(rows)),
         '<h2>Clicks</h2><table><tr><th>What was clicked</th><th>Live lands on</th><th>Rebuild lands on</th><th></th></tr>']
    for c in clicks:
        lv, nw = c['live'], c['new']
        h.append('<tr><td>%s</td><td>%s</td><td>%s</td><td class="%s">%s</td></tr>' % (
            e(c['click']), e(lv.get('landed') or lv.get('error', '')), e(nw.get('landed') or nw.get('error', '')),
            'ok' if c['same'] else 'bad', 'same' if c['same'] else 'DIFFERENT'))
    h.append('</table><p>Video and phone-menu screenshots: <code>shots/live|new/video_*.jpg, phone_*.jpg</code></p>')
    h.append('<h2>Pages</h2><table><tr><th>Page</th><th>Status</th><th>Images live/new</th><th>Videos live/new</th><th>Differences</th></tr>')
    for r in rows:
        lp, np_ = r['live'], r['new']
        h.append('<tr><td><a href="#%s">%s</a></td><td>%s</td><td>%s / %s</td><td>%s / %s</td><td class="%s">%s</td></tr>' % (
            e(shot_name(r['path'])), e(r['path']), e(np_.get('status')), lp.get('images'), np_.get('images'),
            lp.get('videos'), np_.get('videos'), 'bad' if r['issues'] else 'ok',
            '<br>'.join(e(i) for i in r['issues']) or 'none'))
    h.append('</table><h2>Screenshots (left: live, right: rebuild)</h2>')
    for r in rows:
        n = shot_name(r['path'])
        h.append('<h3 id="%s">%s</h3><div class="pair"><figure><img loading="lazy" src="shots/live/%s.jpg"></figure>'
                 '<figure><img loading="lazy" src="shots/new/%s.jpg"></figure></div>' % (e(n), e(r['path']), e(n), e(n)))
    open(os.path.join(OUT, 'report.html'), 'w', encoding='utf-8').write('\n'.join(h))


async def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    new_base = args[0] if args else 'http://127.0.0.1:8792'
    skip_live = '--skip-live' in sys.argv
    for s in ('live', 'new'):
        os.makedirs(os.path.join(OUT, 'shots', s), exist_ok=True)
    paths = page_paths()
    prev = {}
    if skip_live and os.path.exists(os.path.join(OUT, 'results.json')):
        prev = json.load(open(os.path.join(OUT, 'results.json'), encoding='utf-8'))
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(channel='chrome', headless=True)
        sem = asyncio.Semaphore(CONCURRENCY)
        targets = [('new', new_base)] + ([] if prev else [('live', LIVE)])
        result = {'newBase': new_base}
        for site, base in targets:
            print('== pages on %s (%s): %d' % (site, base, len(paths)), flush=True)
            result[site + 'Pages'] = await asyncio.gather(*(visit(browser, base, site, p, sem) for p in paths))
            print('== clicks on %s' % site, flush=True)
            result[site + 'Clicks'] = await scenarios(browser, base, site)
        await browser.close()
    if prev:
        result['livePages'], result['liveClicks'] = prev['livePages'], prev['liveClicks']
    rows, clicks = compare(result['livePages'], result['newPages'], result['liveClicks'], result['newClicks'])
    result['rows'], result['clicks'] = rows, clicks
    json.dump(result, open(os.path.join(OUT, 'results.json'), 'w', encoding='utf-8'), indent=1)
    write_report(rows, clicks, new_base)
    print('\nclicks same: %d/%d   pages without differences: %d/%d' % (
        sum(c['same'] for c in clicks), len(clicks), sum(not r['issues'] for r in rows), len(rows)))
    for c in clicks:
        if not c['same']:
            print('  CLICK %-45s live=%s  new=%s %s' % (c['click'][:45], c['live'].get('landed'), c['new'].get('landed'), c['new'].get('error') or ''))
    for r in rows:
        if r['issues']:
            print('  PAGE  %-45s %s' % (r['path'][:45], ' | '.join(r['issues'])[:300]))
    print('report:', os.path.join(OUT, 'report.html'))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(main())
