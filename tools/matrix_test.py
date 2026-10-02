"""Cross-browser / screen-size test: live Squarespace site vs the rebuild, same pages, same settings.

    python matrix_test.py [new-base-url]          default: https://shaosyucla.github.io/shaosiyuan.com
    python matrix_test.py --only iphone17 ...     run only some setups

Setups: Chrome 1920 / 1366, Edge 1280, Safari engine (WebKit) 1440, iPad Mini, iPhone 17 Pro, iPhone SE,
Android Pixel 7. (Firefox's test build cannot start inside this app's sandbox on Windows.)

Per setup and page, on both sites: full-page screenshot, horizontal overflow, header mode (menu links or
menu button), positions of title / first heading / footer, broken images, script errors. Plus two clicks:
the Let Go video thumbnail, and (phones/tablets with a menu button) open menu -> Contact.
Output: ../compare/matrix/{results.json, report.txt, <setup>/<site>_<page>.jpg}
"""
import asyncio, json, os, re, sys
from playwright.async_api import async_playwright

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'compare', 'matrix')
LIVE = 'https://www.shaosiyuan.com'

PAGES = ['/', '/about', '/contact', '/life', '/life-blog', '/towards-ornithopter', '/moments-mechanical',
         '/jumping-vehicle/let-go', '/towards-ornithopter/final-tests', '/towards-ornithopter/tail-kinematics',
         '/course-projects/inverted-pendulum', '/life-blog/improved-lifestyle']

SETUPS = {
    'chrome1920': dict(engine='chromium', channel='chrome', viewport={'width': 1920, 'height': 1080}),
    'chrome1366': dict(engine='chromium', channel='chrome', viewport={'width': 1366, 'height': 768}),
    'edge1280':   dict(engine='chromium', channel='msedge', viewport={'width': 1280, 'height': 800}),
    'safari1440': dict(engine='webkit', viewport={'width': 1440, 'height': 900}),
    'ipadmini':   dict(engine='webkit', device='iPad Mini'),
    'iphone17':   dict(engine='webkit', device='iPhone 17 Pro'),
    'iphoneSE':   dict(engine='webkit', device='iPhone SE (3rd gen)'),
    'pixel7':     dict(engine='chromium', channel='chrome', device='Pixel 7'),
}

FACTS = r"""() => {
  const vis = e => e && e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden' && getComputedStyle(e).display !== 'none';
  const first = sels => { for (const s of sels) { const e = [...document.querySelectorAll(s)].find(vis); if (e) return e; } return null; };
  const r = e => { if (!e) return null; const b = e.getBoundingClientRect(); return [Math.round(b.left), Math.round(b.top + scrollY), Math.round(b.width), Math.round(b.height)]; };
  const burger = first(['.header-burger-btn', '.menu-toggle']);
  const navLink = first(['.header-display-desktop .header-nav-item a', '.site-nav a']);
  const imgs = [...document.querySelectorAll('main img')].filter(vis);
  return {
    overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    height: document.documentElement.scrollHeight,
    menuMode: burger && vis(burger) ? 'button' : (navLink ? 'links' : 'none'),
    siteTitle: r(first(['.header-display-desktop .header-title a', '.header-display-mobile .header-title a', '.header-title a', '.site-title'])),
    h1: r(first(['main h1'])),
    footer: r(first(['footer p', '.site-footer p'])),
    brokenImages: imgs.filter(i => i.complete && i.naturalWidth === 0 && (i.currentSrc || i.src)).length,
    images: imgs.length,
  };
}"""


def name_of(path):
    return 'home' if path == '/' else re.sub(r'[^A-Za-z0-9]+', '_', path.strip('/'))


async def context_for(pw, browsers, setup):
    key = (setup['engine'], setup.get('channel'))
    if key not in browsers:
        bt = getattr(pw, setup['engine'])
        browsers[key] = await (bt.launch(channel=setup['channel']) if setup.get('channel') else bt.launch())
    opts = dict(pw.devices[setup['device']]) if setup.get('device') else {'viewport': setup['viewport']}
    opts.pop('default_browser_type', None)
    opts['device_scale_factor'] = min(opts.get('device_scale_factor', 1), 2)   # keep screenshots a sane size
    return await browsers[key].new_context(**opts)


async def run_page(ctx, base, path, shot):
    page = await ctx.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)[:150]))
    try:
        resp = await page.goto(base + path, wait_until='load', timeout=60000)
        await page.evaluate('async () => { for (let y=0;y<document.body.scrollHeight;y+=500){scrollTo(0,y);await new Promise(r=>setTimeout(r,70));} scrollTo(0,0); await new Promise(r=>setTimeout(r,500)); }')
        await page.wait_for_timeout(1200)
        facts = await page.evaluate(FACTS)
        facts['status'] = resp.status if resp else None
        await page.screenshot(path=shot, full_page=True, type='jpeg', quality=70)
    except Exception as e:  # noqa: BLE001
        facts = {'error': str(e).split('\n')[0][:160]}
    facts['scriptErrors'] = errors
    await page.close()
    return facts


async def clicks(ctx, base, is_live, shotdir, site):
    out = {}
    page = await ctx.new_page()
    # video thumbnail
    try:
        await page.goto(base + '/jumping-vehicle/let-go', wait_until='load')
        box = page.locator('.sqs-video-wrapper' if is_live else '.video').first
        await box.scroll_into_view_if_needed(timeout=8000)
        await page.wait_for_timeout(1000)
        await box.click(timeout=8000)
        await page.wait_for_timeout(3500)
        src = await box.locator('iframe').first.get_attribute('src', timeout=8000)
        out['video'] = 'player loaded' if src and 'youtube.com/embed/r4e5d9ylyU4' in src else 'no player (%s)' % src
    except Exception as e:  # noqa: BLE001
        out['video'] = 'ERROR ' + str(e).split('\n')[0][:100]
    # menu button (only where the site shows one)
    try:
        await page.goto(base + '/about', wait_until='load')
        await page.wait_for_timeout(1000)
        burger = page.locator(('.header-burger-btn' if is_live else '.menu-toggle') + ':visible').first
        if await burger.count():
            await burger.click(timeout=8000)
            await page.wait_for_timeout(1200)
            await page.screenshot(path=os.path.join(shotdir, site + '_menu_open.jpg'), type='jpeg', quality=70)
            item = page.locator(('.header-menu-nav-item a' if is_live else '.site-nav a') + ':visible',
                                has_text=re.compile(r'^\s*Contact\s*$')).first
            await item.click(timeout=8000)
            await page.wait_for_timeout(2000)
            out['menu'] = 'Contact opened' if '/contact' in page.url else 'landed on ' + page.url
        else:
            out['menu'] = 'no menu button (links shown)'
    except Exception as e:  # noqa: BLE001
        out['menu'] = 'ERROR ' + str(e).split('\n')[0][:100]
    await page.close()
    return out


def compare(live, new):
    issues = []
    if new.get('error') or live.get('error'):
        return ['error: %s / %s' % (live.get('error'), new.get('error'))]
    if new['overflowX'] > 1:
        issues.append('rebuild scrolls sideways by %dpx' % new['overflowX'])
    if new['menuMode'] != live['menuMode']:
        issues.append('menu: live %s, rebuild %s' % (live['menuMode'], new['menuMode']))
    for k in ('siteTitle', 'h1'):
        a, b = live.get(k), new.get(k)
        if bool(a) != bool(b):
            issues.append('%s present live=%s rebuild=%s' % (k, bool(a), bool(b)))
        elif a and b and (abs(a[1] - b[1]) > 8 or abs(a[0] - b[0]) > 8 or abs(a[2] - b[2]) > 12):
            issues.append('%s live %s rebuild %s' % (k, a, b))
    lh, nh = live.get('height', 0), new.get('height', 0)
    if lh and abs(lh - nh) > max(60, 0.04 * lh):
        issues.append('page height live %d rebuild %d' % (lh, nh))
    if new['brokenImages']:
        issues.append('broken images: %d' % new['brokenImages'])
    if new['scriptErrors']:
        issues.append('script errors: %s' % new['scriptErrors'][:2])
    return issues


async def main():
    args = sys.argv[1:]
    only = args[args.index('--only') + 1:] if '--only' in args else None
    pos = [a for a in (args[:args.index('--only')] if '--only' in args else args) if not a.startswith('--')]
    new_base = (pos[0] if pos else 'https://shaosyucla.github.io/shaosiyuan.com').rstrip('/')
    setups = {k: v for k, v in SETUPS.items() if not only or k in only}
    results = {}
    async with async_playwright() as pw:
        browsers = {}
        for sname, setup in setups.items():
            d = os.path.join(OUT, sname)
            os.makedirs(d, exist_ok=True)
            results[sname] = {'pages': {}, 'clicks': {}}
            for site, base in (('live', LIVE), ('new', new_base)):
                ctx = await context_for(pw, browsers, setup)
                sem = asyncio.Semaphore(4)

                async def one(path):
                    async with sem:
                        return path, await run_page(ctx, base, path, os.path.join(d, '%s_%s.jpg' % (site, name_of(path))))
                for path, facts in await asyncio.gather(*(one(p) for p in PAGES)):
                    results[sname]['pages'].setdefault(path, {})[site] = facts
                results[sname]['clicks'][site] = await clicks(ctx, base, site == 'live', d, site)
                await ctx.close()
            print('done', sname, flush=True)
        for b in browsers.values():
            await b.close()
    lines = []
    total = bad = 0
    for sname, res in results.items():
        lines.append('== %s' % sname)
        c = res['clicks']
        same = c['live'] == c['new']
        lines.append('   clicks live %s | rebuild %s %s' % (c['live'], c['new'], 'SAME' if same else 'DIFFERENT'))
        for path, pair in res['pages'].items():
            total += 1
            iss = compare(pair.get('live', {}), pair.get('new', {}))
            if iss:
                bad += 1
                lines.append('   %-40s %s' % (path, ' | '.join(iss)))
    lines.insert(0, 'page checks without differences: %d / %d' % (total - bad, total))
    open(os.path.join(OUT, 'report.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
    json.dump(results, open(os.path.join(OUT, 'results.json'), 'w', encoding='utf-8'), indent=1)
    print('\n'.join(lines))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(main())
