"""Measure vertical gaps between consecutive content elements on live vs rebuild (same page).

    python measure_gaps.py /jumping-vehicle/let-go /towards-ornithopter/final-tests
Prints, for each site, the list of (element, top, height, gap to previous) inside the post body.
"""
import asyncio, sys
from playwright.async_api import async_playwright

LIVE, NEW = 'https://www.shaosiyuan.com', 'http://127.0.0.1:8792'
JS = r"""(live) => {
  const root = document.querySelector(live ? '.blog-item-content' : '.post-body') || document.querySelector('main');
  const els = [...root.querySelectorAll('p, h1, h2, h3, h4, figure, .sqs-video-wrapper, .video, blockquote, hr, .gallery, ul, ol')]
    .filter(e => !e.closest('figcaption') && !(e.tagName === 'P' && e.closest('figure')) && e.offsetParent && e.getBoundingClientRect().height > 0);
  // keep outermost only
  const top = els.filter(e => !els.some(o => o !== e && o.contains(e)));
  const out = []; let prevBottom = null;
  for (const e of top) {
    const r = e.getBoundingClientRect(); const y = Math.round(r.top + scrollY);
    const kind = e.matches('.sqs-video-wrapper, .video') ? 'VIDEO' : e.tagName;
    out.push([kind, (e.innerText || '').trim().slice(0, 28), y, Math.round(r.height), prevBottom === null ? null : y - prevBottom, Math.round(r.width)]);
    prevBottom = Math.round(r.bottom + scrollY);
  }
  return out;
}"""


async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.launch(channel='chrome', headless=True)
        for path in sys.argv[1:]:
            for site, base in (('live', LIVE), ('new', NEW)):
                p = await b.new_page(viewport={'width': 1280, 'height': 800})
                await p.goto(base + path, wait_until='load')
                await p.evaluate('async () => { for (let y=0;y<document.body.scrollHeight;y+=700){scrollTo(0,y);await new Promise(r=>setTimeout(r,80));} scrollTo(0,0); }')
                await p.wait_for_timeout(1500)
                rows = await p.evaluate(JS, site == 'live')
                print('== %s %s' % (site, path))
                for k, t, y, h, gap, w in rows:
                    print('   %-6s gap %-5s h %-5s w %-4s %s' % (k, gap, h, w, t.replace('\n', ' ')))
                await p.close()
        await b.close()

asyncio.run(main())
