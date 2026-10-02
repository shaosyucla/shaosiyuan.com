"""Per post: compare words / images / videos between the Squarespace JSON body and the rebuilt page."""
import json, os, re, glob, html
from bs4 import BeautifulSoup

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
ORIG, SITE = os.path.join(ROOT, 'original'), os.path.join(ROOT, 'site')


def words(soup):
    for t in soup(['style', 'script', 'noscript']):
        t.decompose()
    return re.findall(r'\w+', soup.get_text(' '))


bad = 0
total = 0
for col in ['towards-ornithopter', 'jumping-vehicle', 'moments-mechanical', 'course-projects', 'life-blog']:
    items = []
    for f in sorted(glob.glob(os.path.join(ORIG, col + '*.json'))):
        items += json.load(open(f, encoding='utf-8'))['items']
    for it in items:
        total += 1
        src = BeautifulSoup(it['body'], 'lxml')
        n_img = len({i.get('data-src') or i.get('src') for i in src.select('.image-block img, .gallery-block img.thumb-image')})
        n_vid = len(src.select('.video-block'))
        w_src = words(src)
        out = BeautifulSoup(open(os.path.join(SITE, col, it['urlId'] + '.html'), encoding='utf-8').read(), 'lxml')
        body = out.select_one('.post-body')
        o_img = len(body.select('figure img'))
        o_vid = len(body.select('.video'))   # player iframe, or thumbnail that loads it
        w_out = words(body)
        ok = n_img == o_img and n_vid == o_vid and abs(len(w_src) - len(w_out)) <= 2
        if not ok:
            bad += 1
            print('DIFF %-45s img %d/%d  video %d/%d  words %d/%d' % (
                col + '/' + it['urlId'], n_img, o_img, n_vid, o_vid, len(w_src), len(w_out)))
print('posts checked: %d, with differences: %d' % (total, bad))
