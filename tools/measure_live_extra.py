"""Targeted live-site measurements (Squarespace markup) used to tune site.css."""
import asyncio, json, sys
from playwright.async_api import async_playwright

LIVE = 'https://www.shaosiyuan.com'
DESK, PHONE = {'width': 1280, 'height': 800}, {'width': 375, 'height': 812}

PROBES = {
    # last visible text line of the post body -> pagination title
    'post end gap': ('/jumping-vehicle/let-go', DESK, r"""() => {
        const blocks = [...document.querySelectorAll('.blog-item-content .sqs-block')].filter(b => b.innerText.trim() || b.querySelector('img,iframe,.sqs-video-wrapper'));
        const last = blocks[blocks.length - 1].getBoundingClientRect();
        const pag = document.querySelector('.item-pagination').getBoundingClientRect();
        const title = document.querySelector('.item-pagination-title').getBoundingClientRect();
        const wrap = document.querySelector('.blog-item-wrapper, .blog-item-content-wrapper');
        const cs = e => { const c = getComputedStyle(e); return c.margin + ' / ' + c.padding; };
        return {lastBlockBottom: last.bottom + scrollY, paginationTop: pag.top + scrollY, titleTop: title.top + scrollY,
                contentWrapper: cs(document.querySelector('.blog-item-content-wrapper')),
                content: cs(document.querySelector('.blog-item-content')), comments: !!document.querySelector('.blog-item-comments'),
                between: [...document.querySelectorAll('.blog-item-wrapper > *, article > *')].map(e => e.className.slice(0,40) + ' h' + Math.round(e.getBoundingClientRect().height))};
    }"""),
    'older posts': ('/towards-ornithopter', DESK, r"""() => {
        const p = document.querySelector('.blog-list-pagination'); const a = p.querySelector('a');
        const svg = p.querySelector('svg'); const label = p.querySelector('.blog-list-pagination-link-label, a span');
        const items = [...document.querySelectorAll('.blog-item')]; const lastBottom = Math.max(...items.map(i => i.getBoundingClientRect().bottom + scrollY));
        const r = e => e ? [Math.round(e.getBoundingClientRect().left), Math.round(e.getBoundingClientRect().top + scrollY), Math.round(e.getBoundingClientRect().width), Math.round(e.getBoundingClientRect().height)] : null;
        const c = getComputedStyle(p);
        return {lastCardBottom: lastBottom, pagination: r(p), pagMargin: c.margin, pagPad: c.padding, link: r(a), label: r(label),
                labelFont: label && getComputedStyle(label).font, svg: r(svg), svgHTML: svg && svg.outerHTML.slice(0, 400),
                section: r(document.querySelector('section.content-collection')), footerSection: r(document.querySelector('footer section'))};
    }"""),
    'post pagination svg': ('/jumping-vehicle/let-go', DESK, r"""() => {
        const s = document.querySelector('.item-pagination-icon svg, .item-pagination svg');
        return {svg: s && s.outerHTML.slice(0, 500), stroke: s && getComputedStyle(s.querySelector('path, polyline') || s).strokeWidth};
    }"""),
    'life captions': ('/life', DESK, r"""() => [...document.querySelectorAll('.gallery-masonry-item')].slice(0, 7).map(f => {
        const i = f.querySelector('img'), cap = f.querySelector('.gallery-caption'), p = cap && cap.querySelector('p');
        const r = e => e ? [Math.round(e.getBoundingClientRect().left), Math.round(e.getBoundingClientRect().top + scrollY), Math.round(e.getBoundingClientRect().width), Math.round(e.getBoundingClientRect().height)] : null;
        return {src: (i.getAttribute('data-src') || i.src).split('/').pop().slice(0, 24), fig: r(f), img: r(i), cap: r(cap),
                capPad: cap && getComputedStyle(cap).padding, pFont: p && getComputedStyle(p).font, pMargin: p && getComputedStyle(p).margin};
    })"""),
    'image caption': ('/course-projects/magnetic-levitation', DESK, r"""() => [...document.querySelectorAll('.image-block')].slice(0, 3).map(b => {
        const i = b.querySelector('img'), cap = b.querySelector('figcaption, .image-caption');
        const r = e => e ? [Math.round(e.getBoundingClientRect().left), Math.round(e.getBoundingClientRect().top + scrollY), Math.round(e.getBoundingClientRect().width), Math.round(e.getBoundingClientRect().height)] : null;
        const p = cap && cap.querySelector('p');
        return {img: r(i), cap: r(cap), capStyle: cap && getComputedStyle(cap).padding + ' | ' + getComputedStyle(cap).margin,
                pFont: p && getComputedStyle(p).font, pColor: p && getComputedStyle(p).color, pClass: p && p.className};
    })"""),
    'headings h3 h4': ('/towards-ornithopter/acknowdgement', DESK, r"""() => ['h1','h2','h3','h4'].map(t => {
        const e = document.querySelector('.blog-item-content ' + t); if (!e) return t + ': none';
        const c = getComputedStyle(e); return t + ': ' + c.font + ' margin ' + c.margin;
    })"""),
    'phone layout': ('/contact', PHONE, r"""() => {
        const r = e => e ? [Math.round(e.getBoundingClientRect().left), Math.round(e.getBoundingClientRect().top + scrollY), Math.round(e.getBoundingClientRect().width), Math.round(e.getBoundingClientRect().height)] : null;
        const cw = document.querySelector('main section .content-wrapper');
        const lines = [...document.querySelectorAll('.header-display-mobile .burger-inner > div, .burger-inner div')].filter(d => d.getClientRects().length).map(d => [r(d), getComputedStyle(d).backgroundColor, getComputedStyle(d).opacity]);
        const fw = document.querySelector('footer .content-wrapper');
        const header = document.querySelector('.header-display-mobile') || document.querySelector('header');
        return {contentWrapperPad: cw && getComputedStyle(cw).padding, map: r(document.querySelector('.sqs-block-map, .map-block')),
                burgerLines: lines, header: r(header), headerPad: getComputedStyle(document.querySelector('.header-announcement-bar-wrapper') || header).padding,
                footerWrapperPad: fw && getComputedStyle(fw).padding, footerLinkWS: getComputedStyle(document.querySelector('footer a')).whiteSpace,
                bodyFont: getComputedStyle(document.querySelector('main p')).font};
    }"""),
    'phone menu': ('/about', PHONE, r"""async () => {
        document.querySelector('.header-burger-btn').click(); await new Promise(r => setTimeout(r, 1500));
        const items = [...document.querySelectorAll('.header-menu-nav-item a')].filter(a => a.getClientRects().length);
        const r = e => e ? [Math.round(e.getBoundingClientRect().left), Math.round(e.getBoundingClientRect().top), Math.round(e.getBoundingClientRect().width), Math.round(e.getBoundingClientRect().height)] : null;
        const x = [...document.querySelectorAll('.burger-inner div')].filter(d => d.getClientRects().length).map(d => [r(d), getComputedStyle(d).transform, getComputedStyle(d).backgroundColor]);
        return {items: items.map(a => [a.innerText.trim(), r(a)]), font: items[0] && getComputedStyle(items[0]).font,
                activeDeco: items[1] && getComputedStyle(items[1]).textDecorationLine + ' ' + getComputedStyle(items[1]).backgroundImage.slice(0, 60),
                title: r(document.querySelector('.header-display-mobile .header-title a')), titleColor: getComputedStyle(document.querySelector('.header-display-mobile .header-title a')).color,
                close: x, menuBg: getComputedStyle(document.querySelector('.header-menu-bg') || document.querySelector('.header-menu')).backgroundColor};
    }"""),
    'home hero': ('/', DESK, r"""() => {
        const s = document.querySelector('main section'); const cw = s.querySelector('.content-wrapper');
        const r = e => [Math.round(e.getBoundingClientRect().top + scrollY), Math.round(e.getBoundingClientRect().height)];
        return {section: r(s), cwPad: getComputedStyle(cw).padding, blocks: [...s.querySelectorAll('.sqs-html-content > *')].map(e => e.tagName + ' ' + r(e) + ' m ' + getComputedStyle(e).margin)};
    }"""),
    'life hero': ('/life', DESK, r"""() => {
        const s = document.querySelector('main section'); const cw = s.querySelector('.content-wrapper');
        const r = e => [Math.round(e.getBoundingClientRect().top + scrollY), Math.round(e.getBoundingClientRect().height)];
        return {section: r(s), cwPad: getComputedStyle(cw).padding, blocks: [...s.querySelectorAll('.sqs-html-content > *')].map(e => e.tagName + ' ' + r(e) + ' ' + getComputedStyle(e).font + ' m ' + getComputedStyle(e).margin)};
    }"""),
}


async def main():
    want = sys.argv[1:]
    async with async_playwright() as pw:
        b = await pw.chromium.launch(channel='chrome', headless=True)
        for name, (path, view, js) in PROBES.items():
            if want and not any(name.startswith(w) for w in want):
                continue
            ctx = await b.new_context(viewport=view, is_mobile=view is PHONE, has_touch=view is PHONE)
            p = await ctx.new_page()
            await p.goto(LIVE + path, wait_until='load')
            await p.evaluate('async () => { for (let y=0;y<document.body.scrollHeight;y+=600){scrollTo(0,y);await new Promise(r=>setTimeout(r,60));} scrollTo(0,0); }')
            await p.wait_for_timeout(1500)
            try:
                res = await p.evaluate(js)
            except Exception as e:  # noqa: BLE001
                res = 'ERROR ' + str(e)[:200]
            print('== %s %s\n%s' % (name, path, json.dumps(res, indent=1)[:3000]))
            await ctx.close()
        await b.close()

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(main())
