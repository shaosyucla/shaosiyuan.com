"""Print each page-section of the downloaded pages: theme, classes, background, block tree."""
import os, re, sys
from bs4 import BeautifulSoup

ORIG = os.path.join(os.path.dirname(__file__), '..', 'original')
PAGES = sys.argv[1:] or ['index', 'about', 'life', 'contact', 'towards-ornithopter',
                         'jumping-vehicle', 'moments-mechanical', 'course-projects']


def tree(el, depth=0):
    for ch in el.find_all(recursive=False):
        cls = ' '.join(ch.get('class', []))
        if 'sqs-block' in cls:
            name = ch.get('data-definition-name') or cls.split()[1]
            txt = re.sub(r'\s+', ' ', ch.get_text(' ', strip=True))[:70]
            img = ch.find('img')
            src = (img.get('data-src') or img.get('src') or '')[-45:] if img else ''
            print('  ' * depth, '[blk]', name, '|', txt, '|', src)
        elif 'row' in cls.split() or 'col' in cls.split():
            span = re.search(r'span-(\d+)', cls)
            print('  ' * depth, 'row' if 'row' in cls.split() else 'col' + (span.group(1) if span else ''))
            tree(ch, depth + 1)
        elif ch.name in ('style', 'script'):
            continue
        else:
            tree(ch, depth)


for p in PAGES:
    soup = BeautifulSoup(open(os.path.join(ORIG, p + '.html'), encoding='utf-8').read(), 'lxml')
    print('=' * 10, p)
    for sec in soup.select('main section.page-section'):
        cls = [c for c in sec.get('class', []) if c not in ('page-section',)]
        bg = sec.select_one('.section-background')
        bgimg = bg.find('img') if bg else None
        print('SECTION theme=%s %s' % (sec.get('data-section-theme'), ' '.join(cls)))
        if bgimg:
            print('   bg img', (bgimg.get('data-src') or bgimg.get('src'))[-60:])
        if bg and bg.find('video'):
            print('   bg VIDEO')
        content = sec.select_one('.content') or sec
        if sec.select_one('.collection-content-wrapper') or 'collection-type' in ' '.join(cls):
            print('   <collection list>')
        gal = sec.select('.gallery-grid-item, .gallery-masonry-item, figure.gallery-reel-item')
        if gal:
            print('   gallery items', len(gal), gal[0].find('img').get('data-src', '')[-40:] if gal[0].find('img') else '')
        lay = sec.select_one('.sqs-layout')
        if lay:
            tree(lay, 1)
