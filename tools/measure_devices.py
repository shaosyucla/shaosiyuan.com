"""Measure live vs rebuild on device profiles (WebKit iPhone / iPad) for the phone/tablet layout.

    python measure_devices.py [new-base]
"""
import asyncio, json, sys
from playwright.async_api import async_playwright

LIVE, NEW = 'https://www.shaosiyuan.com', (sys.argv[1] if len(sys.argv) > 1 else 'https://shaosyucla.github.io/shaosiyuan.com')
JS = r"""(live) => {
  const vis = e => e && e.getClientRects().length && getComputedStyle(e).display !== 'none' && getComputedStyle(e).visibility !== 'hidden';
  const all = s => [...document.querySelectorAll(s)].filter(vis);
  const r = e => { if (!e) return null; const b = e.getBoundingClientRect(); return [Math.round(b.left), Math.round(b.top + scrollY), Math.round(b.width), Math.round(b.height)]; };
  const cs = (e, p) => e ? getComputedStyle(e)[p] : null;
  const q = (l, n) => all(live ? l : n)[0];
  const out = {};
  out.header = r(q('.header-display-mobile, header .header-inner', '.site-header'));
  out.title = r(q('.header-display-mobile .header-title a, .header-title a', '.site-title'));
  out.titleFont = cs(q('.header-display-mobile .header-title a, .header-title a', '.site-title'), 'fontSize');
  out.burger = r(q('.header-burger-btn', '.menu-toggle'));
  out.h1 = r(q('main h1', 'main h1'));
  out.galleryItems = all(live ? '.gallery-masonry-item' : '.gallery-section figure').slice(0, 4).map(r);
  out.galleryCaption = cs(q('.gallery-masonry-item .gallery-caption p', '.gallery-section figcaption'), 'fontSize');
  out.galleryCapPad = cs(q('.gallery-masonry-item .gallery-caption', '.gallery-section figcaption'), 'padding');
  const card = q('.blog-item', '.card');
  if (card) {
    const p = s => card.querySelector(s);
    out.card = r(card);
    out.cardParts = live
      ? [r(p('.blog-image-wrapper')), r(p('.blog-meta-section')), r(p('.blog-title')), r(p('.blog-excerpt')), r(p('.blog-more-link'))]
      : [r(p('.card-thumb')), r(p('.card-meta')), r(p('.card-title')), r(p('.card-excerpt')), r(p('.card-more'))];
    out.cardTitleFont = cs(p(live ? '.blog-title' : '.card-title'), 'fontSize');
    out.cards = all(live ? '.blog-item' : '.card').slice(0, 3).map(r);
  }
  out.bodyFont = cs(q('main p', 'main p'), 'fontSize');
  return out;
}"""


async def main():
    async with async_playwright() as pw:
        b = await pw.webkit.launch()
        for dev, paths in (('iPhone 17 Pro', ['/life', '/towards-ornithopter', '/moments-mechanical', '/jumping-vehicle/let-go']),
                           ('iPad Mini', ['/', '/life', '/jumping-vehicle/let-go', '/towards-ornithopter'])):
            for path in paths:
                for site, base in (('live', LIVE), ('new ', NEW)):
                    o = dict(pw.devices[dev]); o.pop('default_browser_type', None); o['device_scale_factor'] = 1
                    ctx = await b.new_context(**o); p = await ctx.new_page()
                    await p.goto(base + path, wait_until='load')
                    await p.evaluate('async () => { for (let y=0;y<document.body.scrollHeight;y+=500){scrollTo(0,y);await new Promise(r=>setTimeout(r,60));} scrollTo(0,0); }')
                    await p.wait_for_timeout(1200)
                    res = await p.evaluate(JS, site == 'live')
                    print('%-13s %-26s %s %s' % (dev, path, site, json.dumps({k: v for k, v in res.items() if v not in (None, [])})))
                    await ctx.close()
        await b.close()

asyncio.run(main())
