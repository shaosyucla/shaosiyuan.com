"""Life gallery on a device profile: every item's box on the live site and the copy, matched by caption text.

    python measure_gallery.py [new-base] [device]        default device: iPhone 17 Pro (WebKit)
"""
import asyncio, sys
from playwright.async_api import async_playwright

LIVE = 'https://www.shaosiyuan.com'
NEW = (sys.argv[1] if len(sys.argv) > 1 else 'https://shaosyucla.github.io/shaosiyuan.com').rstrip('/')
DEV = sys.argv[2] if len(sys.argv) > 2 else 'iPhone 17 Pro'
JS = r"""(live) => {
  const items = [...document.querySelectorAll(live ? '.gallery-masonry-item' : '.gallery-section figure')];
  const g = document.querySelector(live ? '.gallery-masonry-wrapper' : '.gallery-section[data-masonry]');
  const gb = g.getBoundingClientRect();
  const out = items.map(e => {
    const b = e.getBoundingClientRect(), img = e.querySelector('img'), ib = img.getBoundingClientRect();
    const cap = e.querySelector(live ? '.gallery-caption' : 'figcaption');
    return {key: (cap ? cap.innerText : '').trim().slice(0, 24), x: Math.round(b.left), y: Math.round(b.top - gb.top),
            h: Math.round(b.height), imgH: Math.round(ib.height), capH: cap ? Math.round(cap.getBoundingClientRect().height) : 0};
  });
  return {galleryTop: Math.round(gb.top + scrollY), galleryH: Math.round(gb.height), page: document.documentElement.scrollHeight, items: out};
}"""


async def main():
    async with async_playwright() as pw:
        b = await pw.webkit.launch()
        res = {}
        for site, base in (('live', LIVE), ('new', NEW)):
            o = dict(pw.devices[DEV]); o.pop('default_browser_type', None)
            ctx = await b.new_context(**o); p = await ctx.new_page()
            await p.goto(base + '/life', wait_until='load')
            await p.evaluate('async () => { for (let y=0;y<document.body.scrollHeight;y+=400){scrollTo(0,y);await new Promise(r=>setTimeout(r,80));} scrollTo(0,0); }')
            await p.wait_for_timeout(1500)
            res[site] = await p.evaluate(JS, site == 'live')
            await ctx.close()
        await b.close()
    for s in ('live', 'new'):
        print(s, 'gallery top', res[s]['galleryTop'], 'gallery height', res[s]['galleryH'], 'page', res[s]['page'])
    new = {i['key']: i for i in res['new']['items']}
    print('%-26s %-28s %s' % ('caption', 'live x,y,h (img/cap)', 'copy x,y,h (img/cap)'))
    for i in res['live']['items']:
        n = new.get(i['key'], {})
        print('%-26s %4s %5s %4s (%s/%s)   %4s %5s %4s (%s/%s)' % (i['key'][:26], i['x'], i['y'], i['h'], i['imgH'], i['capH'],
              n.get('x'), n.get('y'), n.get('h'), n.get('imgH'), n.get('capH')))

asyncio.run(main())
