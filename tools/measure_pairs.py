"""Measure the same things on the live site and the rebuild, side by side.

    python measure_pairs.py            # all probes
    python measure_pairs.py post list  # only probes whose name starts with these words
Each probe: page path, viewport, and pairs of (label, live selector, rebuild selector).
For each element it prints top/left/width/height (page coordinates) plus a few computed styles.
"""
import asyncio, sys
from playwright.async_api import async_playwright

LIVE, NEW = 'https://www.shaosiyuan.com', 'http://127.0.0.1:8792'
DESK, PHONE = {'width': 1280, 'height': 800}, {'width': 375, 'height': 812}

PROBES = [
    ('post pagination', '/moments-mechanical/die-forelle', DESK, [
        ('last body element', '.blog-item-content .sqs-block:last-child', '.post-body .blk:last-of-type'),
        ('pagination row', '.item-pagination', '.post-pagination'),
        ('prev link', '.item-pagination-link--prev', '.post-pagination .prev'),
        ('next link', '.item-pagination-link--next', '.post-pagination .next'),
        ('next title', '.item-pagination-link--next .item-pagination-title', '.post-pagination .next span:first-child'),
        ('next icon', '.item-pagination-link--next svg', '.post-pagination .next .arrow'),
        ('footer text', 'footer p', '.site-footer p'),
    ]),
    ('post title', '/life-blog/fiorentino-schubert', DESK, [
        ('date line', '.blog-item-top-wrapper .blog-meta-section', '.post-meta'),
        ('title', '.entry-title', '.post-title'),
        ('first body element', '.blog-item-content .sqs-block', '.post-body .blk'),
    ]),
    ('list masonry', '/jumping-vehicle', DESK, [
        ('list section', '.blog-masonry', '.blog-list'),
        ('card 1', '.blog-item:nth-of-type(1)', '.card:nth-of-type(1)'),
        ('card 1 image', '.blog-item:nth-of-type(1) .blog-image-wrapper', '.card:nth-of-type(1) .card-thumb'),
        ('card 1 meta', '.blog-item:nth-of-type(1) .blog-meta-section', '.card:nth-of-type(1) .card-meta'),
        ('card 1 title', '.blog-item:nth-of-type(1) .blog-title', '.card:nth-of-type(1) .card-title'),
        ('card 1 excerpt', '.blog-item:nth-of-type(1) .blog-excerpt', '.card:nth-of-type(1) .card-excerpt'),
        ('card 1 read more', '.blog-item:nth-of-type(1) .blog-more-link', '.card:nth-of-type(1) .card-more'),
        ('card 3', '.blog-item:nth-of-type(3)', '.card:nth-of-type(3)'),
        ('footer text', 'footer p', '.site-footer p'),
    ]),
    ('list grid', '/moments-mechanical', DESK, [
        ('list section', '.blog-basic-grid', '.blog-list'),
        ('card 1', '.blog-item:nth-of-type(1)', '.card:nth-of-type(1)'),
        ('card 1 image', '.blog-item:nth-of-type(1) .image-wrapper, .blog-item:nth-of-type(1) .blog-basic-grid--image', '.card:nth-of-type(1) .card-thumb'),
        ('card 1 date', '.blog-item:nth-of-type(1) .blog-date', '.card:nth-of-type(1) .card-meta'),
        ('card 1 title', '.blog-item:nth-of-type(1) .blog-title', '.card:nth-of-type(1) .card-title'),
        ('card 1 excerpt', '.blog-item:nth-of-type(1) .blog-excerpt', '.card:nth-of-type(1) .card-excerpt'),
        ('card 1 read more', '.blog-item:nth-of-type(1) .blog-more-link', '.card:nth-of-type(1) .card-more'),
        ('card 2', '.blog-item:nth-of-type(2)', '.card:nth-of-type(2)'),
        ('card 3', '.blog-item:nth-of-type(3)', '.card:nth-of-type(3)'),
    ]),
    ('list older', '/towards-ornithopter', DESK, [
        ('older link', '.blog-list-pagination a, .blog-list-pagination-link', '.list-pagination .next'),
        ('older icon', '.blog-list-pagination svg', '.list-pagination .next .arrow'),
        ('footer text', 'footer p', '.site-footer p'),
    ]),
    ('list empty', '/course-projects/category/ME350', DESK, [
        ('collection section', 'section.content-collection', '.blog-list'),
        ('footer text', 'footer p', '.site-footer p'),
    ]),
    ('page empty', '/new-page', DESK, [
        ('main', 'main', 'main'),
        ('footer text', 'footer p', '.site-footer p'),
    ]),
    ('quote', '/towards-ornithopter/aristotle-and-glider', DESK, [
        ('quote text', '.sqs-block-quote blockquote, .quote-block blockquote', 'blockquote p'),
        ('quote source', '.sqs-block-quote figcaption, .quote-block .source', 'blockquote cite'),
    ]),
    ('rule', '/course-projects/non-required-courses', DESK, [
        ('hr', 'hr', 'hr'),
        ('ul', '.blog-item-content ul', '.post-body ul'),
        ('li', '.blog-item-content li', '.post-body li'),
    ]),
    ('headings', '/moments-mechanical', DESK, [
        ('h1', 'main h1', 'main h1'),
        ('h2', 'main h2', 'main h2'),
    ]),
    ('gallery block', '/course-projects/airpuck-and-hovercraft', DESK, [
        ('slide 1', '.sqs-gallery .slide:nth-of-type(1)', '.gallery figure:nth-of-type(1)'),
        ('slide 2', '.sqs-gallery .slide:nth-of-type(2)', '.gallery figure:nth-of-type(2)'),
        ('slide 3', '.sqs-gallery .slide:nth-of-type(3)', '.gallery figure:nth-of-type(3)'),
    ]),
    ('life gallery', '/life', DESK, [
        ('hero h1', 'main h1', 'main h1'),
        ('item 1', '.gallery-masonry-item:nth-of-type(1)', '.gallery-section figure'),
        ('item 1 img', '.gallery-masonry-item:nth-of-type(1) img', '.gallery-section figure img'),
        ('item 2', '.gallery-masonry-item:nth-of-type(2)', '.gallery-section .masonry-col:nth-child(2) figure'),
        ('item 2 caption', '.gallery-masonry-item:nth-of-type(2) .gallery-caption, .gallery-masonry-item:nth-of-type(2) figcaption', '.gallery-section .masonry-col:nth-child(2) figcaption'),
        ('item 4', '.gallery-masonry-item:nth-of-type(4)', '.gallery-section .masonry-col:nth-child(1) figure:nth-child(2)'),
    ]),
    ('hero', '/', DESK, [('home h1', 'main h1', 'main h1')]),
    ('hero2', '/towards-ornithopter', DESK, [('h1', 'main h1', 'main h1'),
                                              ('chevron', 'section:nth-of-type(2) img', 'section:nth-of-type(2) img')]),
    ('hero3', '/jumping-vehicle', DESK, [('h1', 'main h1', 'main h1')]),
    ('phone header', '/contact', PHONE, [
        ('title', '.header-display-mobile .header-title a, .header-title-text a', '.site-title'),
        ('burger', '.header-display-mobile .header-burger-btn, .header-burger-btn', '.menu-toggle'),
        ('burger line', '.header-display-mobile .burger-inner div, .burger-inner div', '.menu-toggle span'),
        ('section', 'main section', 'main section'),
        ('h2', 'main h2', 'main h2'),
        ('footer', 'footer .sqs-layout, footer .content', '.site-footer .section-inner'),
        ('footer link', 'footer a', '.site-footer a'),
    ]),
]

JS = r"""(sels) => sels.map(sel => {
  const els = sel ? [...document.querySelectorAll(sel)].filter(e => e.getClientRects().length) : [];
  const e = els[0];
  if (!e) return null;
  const r = e.getBoundingClientRect(), c = getComputedStyle(e);
  return {n: els.length, top: Math.round(r.top + scrollY), bottom: Math.round(r.bottom + scrollY), left: Math.round(r.left),
          width: Math.round(r.width), height: Math.round(r.height),
          font: c.fontFamily.split(',')[0].replace(/"/g, '') + ' ' + c.fontSize + '/' + c.lineHeight + ' w' + c.fontWeight,
          color: c.color, margin: c.margin, padding: c.padding, ws: c.whiteSpace, align: c.textAlign,
          border: c.borderTop, bg: c.backgroundColor, opacity: c.opacity, minh: c.minHeight};
})"""


async def measure(browser, base, path, view, sels):
    ctx = await browser.new_context(viewport=view, is_mobile=view is PHONE, has_touch=view is PHONE)
    p = await ctx.new_page()
    await p.goto(base + path, wait_until='load')
    await p.evaluate('async () => { for (let y=0;y<document.body.scrollHeight;y+=600){scrollTo(0,y);await new Promise(r=>setTimeout(r,60));} scrollTo(0,0); }')
    await p.wait_for_timeout(1500)
    out = await p.evaluate(JS, sels)
    await ctx.close()
    return out


async def main():
    want = sys.argv[1:]
    async with async_playwright() as pw:
        b = await pw.chromium.launch(channel='chrome', headless=True)
        for name, path, view, pairs in PROBES:
            if want and not any(name.startswith(w) for w in want):
                continue
            live = await measure(b, LIVE, path, view, [p[1] for p in pairs])
            new = await measure(b, NEW, path, view, [p[2] for p in pairs])
            print('== %s  %s  %dpx' % (name, path, view['width']))
            for (label, _, _), l, n in zip(pairs, live, new):
                for site, v in (('live', l), ('new ', n)):
                    if not v:
                        print('   %-18s %s  (not found)' % (label, site)); continue
                    print('   %-18s %s top %5d bot %5d left %4d w %4d h %4d | %s | m %s | p %s | %s %s %s' % (
                        label, site, v['top'], v['bottom'], v['left'], v['width'], v['height'], v['font'], v['margin'],
                        v['padding'], v['color'], v['ws'], v['align']))
        await b.close()

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(main())
