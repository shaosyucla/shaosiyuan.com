"""Measure collage image blocks (photo + grey card) on the live site and the copy at several window widths.

    python measure_collage.py [new-base] [--live-only] [p=/path ...]
Prints per width: block width, narrow class (live), photo / card boxes relative to the block.
"""
import asyncio, json, sys
from playwright.async_api import async_playwright

LIVE = 'https://www.shaosiyuan.com'
args = [a for a in sys.argv[1:] if not a.startswith('--') and not a.startswith('p=')]
NEW = (args[0] if args else 'https://shaosyucla.github.io/shaosiyuan.com').rstrip('/')
PAGES = ([a[2:] for a in sys.argv[1:] if a.startswith('p=')]           # p=/path limits the pages
         or ['/life-blog/improved-lifestyle', '/towards-ornithopter/final-tests', '/towards-ornithopter/wing-structure'])
WIDTHS = [1280, 1024, 900, 820, 800, 799, 790, 768, 767, 700, 600, 500, 393, 375]

JS = r"""(live) => {
  const r = (e, o) => { if (!e) return null; const b = e.getBoundingClientRect();
    return [Math.round(b.left - o.left), Math.round(b.top - o.top), Math.round(b.width), Math.round(b.height)]; };
  const blocks = live ? [...document.querySelectorAll('.design-layout-collage')] : [...document.querySelectorAll('figure.collage')];
  return blocks.map(bl => {
    const o = bl.getBoundingClientRect();
    const img = live ? bl.querySelector('.intrinsic') : bl.querySelector(':scope > img, :scope > a');
    const card = live ? bl.querySelector('.image-card') : bl.querySelector('figcaption');
    const cs = getComputedStyle(bl);
    return {w: Math.round(o.width), h: Math.round(o.height),
            narrow: live ? bl.classList.contains('sqs-narrow-width') : null,
            pos: live ? [...bl.classList].filter(c => c.startsWith('image-position')).join() : bl.className,
            img: r(img, o), card: r(card, o),
            pad: live ? cs.getPropertyValue('--image-block-collage-image-content-padding') : getComputedStyle(card).paddingTop};
  });
}"""


async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.launch(channel='chrome')
        sites = ([] if '--new-only' in sys.argv else [('live', LIVE)]) + ([] if '--live-only' in sys.argv else [('new', NEW)])
        for path in PAGES:
            for w in WIDTHS:
                for site, base in sites:
                    ctx = await b.new_context(viewport={'width': w, 'height': 900})
                    p = await ctx.new_page()
                    await p.goto(base + path, wait_until='load')
                    await p.wait_for_timeout(1500)
                    res = await p.evaluate(JS, site == 'live')
                    print('%-36s %4d %-4s %s' % (path, w, site, json.dumps(res)), flush=True)
                    await ctx.close()
        await b.close()

asyncio.run(main())
