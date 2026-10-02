"""One-time import: Squarespace dumps in ..\\original -> clean editable sources in ..\\src
and downloaded images/files in ..\\site\\img, ..\\site\\files.

Run once (re-running overwrites src/ — do not re-run after hand edits):
    python import_squarespace.py
Then build the site with build.py.
"""
import html as htmllib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup, NavigableString, Comment

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ORIG = os.path.join(ROOT, 'original')
SRC = os.path.join(ROOT, 'src')
SITE = os.path.join(ROOT, 'site')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36'
HOST = 'https://www.shaosiyuan.com'

# plain pages: the four in the menu plus the three unlisted ones from sitemap.xml
# plus pages found only by crawling links (tools/crawl_live.py): introduction-to-password, life-blog
PLAIN = ['index', 'about', 'life', 'contact', 'allapplicationdocuments', 'new-page', 'new-page-1',
         'introduction-to-password', '404']   # original/404.html = live response for a missing URL
COLLECTIONS = ['towards-ornithopter', 'jumping-vehicle', 'moments-mechanical', 'course-projects', 'life-blog']

downloads = {}        # remote url -> local site path ("/img/x.jpg")
used_names = set()


# ---------------------------------------------------------------- assets
def local_name(url, folder):
    """Stable readable local name: <file>-<6 chars of squarespace id>.<ext>."""
    path = urllib.parse.urlparse(url).path
    parts = [urllib.parse.unquote(p) for p in path.split('/') if p]
    fname = parts[-1].replace('+', ' ')
    stem, ext = os.path.splitext(fname)
    ext = ext.lower() or '.jpg'
    if ext == '.jpeg':
        ext = '.jpg'
    tag = ''
    if len(parts) >= 2:
        m = re.search(r'-([A-Z0-9]{6})', parts[-2])
        tag = '-' + m.group(1) if m else ''
    stem = re.sub(r'[^A-Za-z0-9_-]+', '-', stem).strip('-') or 'image'
    name = stem + tag + ext
    n = 2
    while name in used_names:
        name = '%s%s-%d%s' % (stem, tag, n, ext)
        n += 1
    used_names.add(name)
    return '/%s/%s' % (folder, name)


def asset(url, folder='img'):
    """Register a remote asset and return its site-root path."""
    if not url:
        return ''
    url = htmllib.unescape(url).split('?')[0]
    if url.startswith('//'):
        url = 'https:' + url
    if url.startswith('/s/'):
        url = HOST + url
        folder = 's'   # same path as Squarespace (/s/<name>), so old file links keep working
    if url not in downloads:
        downloads[url] = local_name(url, folder)
    return downloads[url]


def fetch_all():
    def get(item):
        url, local = item
        dest = os.path.join(SITE, local.lstrip('/').replace('/', os.sep))
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            return None
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        q = '' if (local.endswith('.gif') or '/s/' in local) else '?format=1500w'
        for attempt in range(3):
            try:
                req = urllib.request.Request(url + q, headers={'User-Agent': UA})
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = r.read()
                open(dest, 'wb').write(data)
                return None
            except Exception as e:  # noqa: BLE001
                err = e
                time.sleep(1 + attempt)
        return '%s -> %s' % (url, err)

    with ThreadPoolExecutor(8) as ex:
        errs = [e for e in ex.map(get, downloads.items()) if e]
    print('assets:', len(downloads), 'failed:', len(errs))
    for e in errs:
        print('  FAIL', e)


# ---------------------------------------------------------------- links
def fix_href(href):
    if not href:
        return href
    href = htmllib.unescape(href).strip().replace('\\', '/')
    for pre in ('https://www.shaosiyuan.com', 'http://www.shaosiyuan.com', 'https://shaosiyuan.com'):
        if href.startswith(pre):
            href = href[len(pre):] or '/'
    if href.startswith('/s/'):
        return asset(href, 's')
    if href.startswith('/') and not href.startswith('//'):
        path, _, frag = href.partition('#')
        path = path.split('?')[0].rstrip('/')
        if path in ('', '/home'):
            out = '/index.html'
        elif path.endswith('.html') or '.' in path.rsplit('/', 1)[-1]:
            out = path
        else:
            out = path + '.html'
        return out + ('#' + frag if frag else '')
    return href


def soupify(raw):
    """Parse Squarespace HTML. Its text is white-space:pre-wrap, and BeautifulSoup collapses
    whitespace-only runs, so deliberate runs of spaces in text become no-break spaces first."""
    def keep(m):
        text = m.group(1)
        if '\n' in text:   # template indentation between tags, not author text
            return m.group(0)
        return '>' + re.sub(r' {2,}', lambda r: ' ' + '\u00a0' * (len(r.group(0)) - 1), text) + '<'
    return BeautifulSoup(re.sub(r'>([^<]+)<', keep, raw), 'lxml')


# ---------------------------------------------------------------- blocks
KEEP_ATTR = {'href', 'src', 'alt', 'title', 'colspan', 'rowspan'}
INLINE_CLASS = {'sqsrte-large': 'large', 'sqsrte-small': 'small', 'sqsrte-text-color--accent': 'accent'}


def clean_text_html(container):
    """Return cleaned inner HTML of a Squarespace rich-text container."""
    for bad in container.find_all(['style', 'script']):
        bad.decompose()
    for c in container.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    for el in container.find_all(True):
        attrs = {}
        style = el.get('style', '')
        keep_style = []
        m = re.search(r'text-align:\s*(center|right|justify)', style)
        if m:
            keep_style.append('text-align:%s' % m.group(1))
        m = re.search(r'margin-left:\s*(\d+px)', style)
        if m:                                   # indented paragraph (Squarespace indent button)
            keep_style.append('margin-left:%s' % m.group(1))
        if keep_style:
            attrs['style'] = ';'.join(keep_style)
        if el.name == 'span' and re.search(r'text-decoration:\s*underline', style):
            el.name = 'u'                       # underlined text that is not a link
        cls = [INLINE_CLASS[c] for c in el.get('class', []) if c in INLINE_CLASS]
        if cls:
            attrs['class'] = ' '.join(cls)
        for k in KEEP_ATTR:
            if el.has_attr(k):
                attrs[k] = el[k]
        if el.name == 'a':
            attrs['href'] = fix_href(el.get('href', ''))
            if el.get('target') == '_blank':
                attrs['target'] = '_blank'
                attrs['rel'] = 'noopener'
        if el.name == 'img':
            attrs['src'] = asset(el.get('data-src') or el.get('src'))
        el.attrs = attrs
    out = ''.join(str(c) for c in container.contents).strip()
    # empty paragraph = one blank line on Squarespace (also when it carries an alignment style)
    out = re.sub(r'<p((?: style="[^"]*")?)></p>', r'<p class="blank"\1></p>', out)
    return out


def block_kind(b):
    if b.get('data-definition-name'):
        return b['data-definition-name'].split('.')[-1]
    for c in b.get('class', []):
        if c.endswith('-block') and c != 'sqs-block':
            return c[:-6]
    return 'unknown'


def convert_image(b):
    img = b.find('img')
    if not img:
        return ''
    src = asset(img.get('data-src') or img.get('data-image') or img.get('src'))
    alt = img.get('alt', '')
    dims = img.get('data-image-dimensions', '')
    wh = ''
    if re.match(r'\d+x\d+$', dims):
        w, h = dims.split('x')
        wh = ' width="%s" height="%s"' % (w, h)
    wrap = b.select_one('.image-block-outer-wrapper')
    wcls = ' '.join(wrap.get('class', [])) if wrap else ''
    cap_el = None if 'layout-caption-hidden' in wcls else (b.find('figcaption') or b.select_one('.image-caption'))
    cap = clean_text_html(cap_el) if cap_el else ''
    # Squarespace crop box: the image is shown cut to a stored aspect ratio around its focal point
    crop = ''
    box = b.select_one('.sqs-image-shape-container-element')
    m = re.search(r'padding-bottom:\s*([\d.]+)%', box.get('style', '')) if box else None
    if m and re.match(r'\d+x\d+$', dims):
        pb = float(m.group(1))
        w, h = (int(x) for x in dims.split('x'))
        if abs(pb - h * 100.0 / w) > 0.5:
            fx, fy = (float(v) for v in (img.get('data-image-focal-point') or '0.5,0.5').split(','))
            # data-focal: site.js centres this point in the box, as Squarespace does
            crop = ' style="aspect-ratio:100/%.4g;object-fit:cover" data-focal="%.4g,%.4g"' % (pb, fx, fy)
    tag = '<img src="%s" alt="%s"%s%s loading="lazy">' % (src, htmllib.escape(alt, quote=True), wh, crop)
    a = img.find_parent('a') or b.select_one('a.sqs-block-image-link, a.image-slide-anchor')
    if a and a.get('href'):
        extra = ' target="_blank" rel="noopener"' if a.get('target') == '_blank' else ''
        tag = '<a href="%s"%s>%s</a>' % (fix_href(a['href']), extra, tag)
    fig = '<figure>'
    figure_el = b.select_one('figure.sqs-block-image-figure')
    m = re.search(r'max-width:\s*(\d+)px', figure_el.get('style', '')) if figure_el else None
    if m and int(m.group(1)) < 1200:   # small image: shown at its own width, centred (caption as wide as the image)
        fig = '<figure style="max-width:%spx">' % m.group(1)
    if 'design-layout-collage' in wcls and cap:
        side = 'right' if 'image-position-right' in wcls else 'left'
        fig = '<figure class="collage image-%s">' % side
    if cap:
        return '%s%s<figcaption>%s</figcaption></figure>' % (fig, tag, cap)
    return '%s%s</figure>' % (fig, tag)


def convert_video(b):
    w = b.select_one('[data-html]')
    raw = htmllib.unescape(w['data-html']) if w else ''
    m = re.search(r'src="([^"]+)"', raw)
    if not m:
        a = b.find('iframe')
        src = a.get('src') if a else ''
    else:
        src = m.group(1)
    if not src:
        return '<!-- video block without source -->'
    src = src.replace('&amp;', '&')
    if src.startswith('//'):
        src = 'https:' + src
    if 'embedly.com' in src:  # unwrap the Embedly widget to the real player URL
        inner = urllib.parse.parse_qs(urllib.parse.urlparse(src).query).get('src', [''])[0]
        src = 'https:' + inner if inner.startswith('//') else inner or src
    # keep only the parameters that change what the viewer sees
    base, _, query = src.partition('?')
    keep = [p for p in query.split('&') if p.split('=')[0] in ('rel', 't', 'start', 'h')]
    src = base + ('?' + '&'.join(keep) if keep else '')
    t = re.search(r'title="([^"]*)"', raw)
    title = t.group(1) if t else 'Video'
    # box shape: Squarespace stores it as padding-bottom % (56.25% = 16:9); keep non-16:9 shapes (4:3, portrait)
    shape = ''
    wrapper = b.select_one('.embed-block-wrapper')
    m = re.search(r'padding-bottom:\s*([\d.]+)%', wrapper.get('style', '')) if wrapper else None
    if m and abs(float(m.group(1)) - 56.25) > 0.6:
        shape = ' style="aspect-ratio:100/%.4g"' % float(m.group(1))
    # custom thumbnail chosen in Squarespace: show it with a play button; site.js swaps in the player on click
    poster = b.select_one('.sqs-video-overlay img')
    if poster and (poster.get('data-src') or poster.get('src')):
        fx, fy = (float(v) for v in (poster.get('data-image-focal-point') or '0.5,0.5').split(','))
        pos = '' if (fx, fy) == (0.5, 0.5) else ' data-focal="%.4g,%.4g"' % (fx, fy)
        return ('<div class="video" data-embed="%s"%s><img src="%s" alt="Play video: %s"%s loading="lazy"></div>'
                % (src, shape, asset(poster.get('data-src') or poster.get('src')), htmllib.escape(title, quote=True), pos))
    return ('<div class="video"%s><iframe src="%s" title="%s" '
            'allow="autoplay; fullscreen; picture-in-picture" allowfullscreen loading="lazy"></iframe></div>'
            % (shape, src, htmllib.escape(title, quote=True)))


def convert_button(b):
    a = b.find('a')
    if not a:
        return ''
    cont = b.select_one('.sqs-block-button-container')
    align = 'center'
    if cont:
        m = re.search(r'--(left|center|right)', ' '.join(cont.get('class', [])))
        align = m.group(1) if m else 'center'
    return '<p class="button-row %s"><a class="button" href="%s">%s</a></p>' % (
        align, fix_href(a.get('href', '')), a.get_text(strip=True))


def convert_quote(b):
    q = b.find('blockquote')
    src = b.find('figcaption')
    # keep the quote's line breaks (verse), drop Squarespace's wrapper tags
    inner = ''.join(str(c) for c in q.contents) if q else ''
    inner = re.sub(r'<br\s*/?>', '\x00', inner)
    text = re.sub(r'<[^>]+>', '', inner)
    text = re.sub(r'[ \t\r\n]+', ' ', text).replace('\x00', '<br>')
    text = re.sub(r'\s*<br>\s*', '<br>', text).strip().strip('“”"').strip()
    cite = src.get_text(' ', strip=True).lstrip('—- ').strip() if src else ''
    out = '<blockquote><p>“%s”</p>' % text
    if cite:
        out += '<cite>— %s</cite>' % htmllib.escape(cite, quote=False)
    return out + '</blockquote>'


def convert_map(b):
    ctx = b.select_one('[data-context]')
    try:
        d = json.loads(ctx['data-context'])
        loc = d['location']
        lat, lng, z = loc['markerLat'], loc['markerLng'], loc.get('mapZoom', 13)
    except Exception:  # noqa: BLE001
        lat, lng, z = 42.2931159, -83.7136987, 13
    return ('<div class="map"><iframe src="https://maps.google.com/maps?q=%s,%s&z=%s&output=embed" '
            'title="Map"></iframe></div>' % (lat, lng, z))


def convert_gallery_block(b):
    js = {}
    try:
        js = json.loads(b.get('data-block-json', '{}'))
    except Exception:  # noqa: BLE001
        pass
    per = js.get('thumbnails-per-row', 3)
    gap = js.get('padding')
    figs = []
    for img in b.select('img.thumb-image'):
        src = asset(img.get('data-src') or img.get('data-image'))
        figs.append('<figure><img src="%s" alt="%s" loading="lazy"></figure>'
                    % (src, htmllib.escape(img.get('alt', ''), quote=True)))
    style = ' style="gap:%spx"' % gap if isinstance(gap, (int, float)) else ''
    return '<div class="gallery cols-%s"%s>\n%s\n</div>' % (per, style, '\n'.join(figs))


def convert_block(b):
    k = block_kind(b)
    if k == 'html':
        c = b.select_one('.sqs-html-content')
        return clean_text_html(c) if c else ''
    if k == 'image':
        return convert_image(b)
    if k == 'video':
        return convert_video(b)
    if k == 'button':
        return convert_button(b)
    if k == 'quote':
        return convert_quote(b)
    if k == 'horizontalrule':
        return '<hr>'
    if k == 'map':
        return convert_map(b)
    if k == 'gallery':
        return convert_gallery_block(b)
    if k == 'spacer':
        return SPACER
    print('   ! unhandled block', k)
    return '<!-- unhandled block: %s -->' % k


SPACER = '<div class="spacer"></div>'
SPACER_BLOCK = '<div class="blk blk-spacer">%s</div>' % SPACER


def wrap_block(b, h):
    """One Squarespace block = one <div class="blk">; CSS gives it Squarespace's 17 px top/bottom padding.
    A floated block (text wraps around it) takes span-N / parent-column-span of the column: --float."""
    cls = b.get('class', [])
    side = 'float-right' if 'float-right' in cls else 'float-left' if 'float-left' in cls else ''
    if side:
        parent = b.find_parent(lambda t: t.name == 'div' and 'col' in t.get('class', []))
        ratio = col_span(b) / float(col_span(parent) if parent else 12)
        return '<div class="blk blk-%s %s" style="--float:%.4g">%s</div>' % (block_kind(b), side, ratio, h)
    return '<div class="blk blk-%s">%s</div>' % (block_kind(b), h)


def col_span(col):
    m = next((re.match(r'span-(\d+)$', c) for c in col.get('class', []) if re.match(r'span-(\d+)$', c)), None)
    return int(m.group(1)) if m else 12


def convert_layout(el, depth=0):
    """Convert sqs-layout row/col/block tree into simple nested divs.

    Squarespace nested rows count spans relative to the parent column (a row inside a span-8 column
    has spans summing to 8). Output spans are rescaled so every row sums to 12."""
    out = []
    pad = '  ' * depth
    total = 12
    if 'row' in el.get('class', []):
        total = sum(col_span(c) for c in el.find_all(recursive=False) if 'col' in c.get('class', [])) or 12
    for ch in el.find_all(recursive=False):
        cls = ch.get('class', [])
        if 'sqs-block' in cls:
            h = convert_block(ch)
            if h:
                out.append(pad + wrap_block(ch, h))
        elif 'row' in cls:
            out.append(pad + '<div class="row">')
            out.extend(convert_layout(ch, depth + 1))
            out.append(pad + '</div>')
        elif 'col' in cls:
            n = col_span(ch) * 12 / total
            if abs(n - round(n)) < 0.01:
                span, style = 'span-%d' % round(n), ''
            else:   # widths that are not whole twelfths (e.g. 2 of 10)
                span, style = 'span-x', ' style="width:%.4g%%"' % (n / 12 * 100)
            inner = convert_layout(ch, depth + 1)
            # a column holding only spacers is just horizontal offset
            if all(s.strip() in ('', SPACER_BLOCK) for s in inner):
                inner = []
            if n == 0 and not inner:
                continue
            if not inner:
                out.append(pad + '<div class="col %s empty"%s></div>' % (span, style))
            else:
                out.append(pad + '<div class="col %s"%s>' % (span, style))
                out.extend(inner)
                out.append(pad + '</div>')
        elif ch.name in ('style', 'script', 'noscript'):
            continue
        else:
            out.extend(convert_layout(ch, depth))
    return out


def simplify(lines):
    """Drop single-column rows (row > col.span-12 > content) to keep sources readable."""
    s = '\n'.join(lines)
    for _ in range(3):
        s = re.sub(r'(?m)^(\s*)<div class="row">\n\s*<div class="col span-12">\n(.*?)\n\s*</div>\n\1</div>$',
                   lambda m: m.group(2), s, flags=re.S)
    return s


def layout_html(layout_el):
    return simplify(convert_layout(layout_el))


# ---------------------------------------------------------------- sections
def section_attrs(sec):
    cls = sec.get('class', [])
    theme = sec.get('data-section-theme') or 'white'
    attrs = {'theme': theme}
    for c in cls:
        for key in ('section-height', 'content-width', 'horizontal-alignment', 'vertical-alignment'):
            if c.startswith(key + '--'):
                attrs[key.split('-')[0] if key != 'section-height' else 'height'] = c.split('--')[1]
    m = re.search(r'min-height:\s*(\d+)vh', sec.get('style', ''))
    if m:
        attrs['minh'] = m.group(1)
    bg = sec.select_one('.section-background img')
    if bg:
        attrs['bg'] = asset(bg.get('data-src') or bg.get('src'))
        attrs['focal'] = bg.get('data-image-focal-point') or ''
        ov = sec.select_one('.section-background-overlay')
        if ov and ov.get('style'):
            m = re.search(r'opacity:\s*([\d.]+)', ov['style'])
            if m:
                attrs['overlay'] = m.group(1)
    return attrs


def section_open(a, extra_class=''):
    cls = ['section', 'theme-' + a['theme']]
    if a.get('height'):
        cls.append('height-' + a['height'])
    if a.get('content'):
        cls.append('width-' + a['content'])
    if a.get('horizontal'):
        cls.append('align-' + a['horizontal'])
    if a.get('vertical'):
        cls.append('valign-' + a['vertical'])
    if extra_class:
        cls.append(extra_class)
    props = []
    if a.get('minh'):
        props.append('min-height:%svh' % a['minh'])
    if a.get('overlay'):
        props.append('--overlay:%s' % a['overlay'])
    style = ' style="%s"' % ';'.join(props) if props else ''
    head = '<section class="%s"%s>' % (' '.join(cls), style)
    if a.get('bg'):
        focal = ' data-focal="%s"' % a['focal'] if a.get('focal') and a['focal'] != '0.5,0.5' else ''
        head += '\n  <img class="section-bg" src="%s" alt=""%s>' % (a['bg'], focal)
    return head


def convert_gallery_section(sec):
    items = []
    for it in sec.select('.gallery-grid-item, .gallery-masonry-item'):
        img = it.find('img')
        if not img:
            continue
        src = asset(img.get('data-src') or img.get('src'))
        cap_el = it.select_one('.gallery-caption-content, .gallery-caption')
        cap = clean_text_html(cap_el) if cap_el else ''
        alt = htmllib.escape(img.get('alt', ''), quote=True)
        dims = img.get('data-image-dimensions', '')
        wh = ' width="%s" height="%s"' % tuple(dims.split('x')) if re.match(r'\d+x\d+$', dims) else ''
        tag = '<img src="%s" alt="%s"%s loading="lazy">' % (src, alt, wh)
        a = it.find('a', href=True)
        if a:  # click-through link set on the gallery image
            tag = '<a href="%s">%s</a>' % (fix_href(a['href']), tag)
        f = '  <figure>%s' % tag
        if cap:
            f += '<figcaption>%s</figcaption>' % cap
        items.append(f + '</figure>')
    return '<div class="gallery gallery-section" data-masonry="3">\n%s\n</div>' % '\n'.join(items)


def convert_page(name):
    soup = soupify(open(os.path.join(ORIG, name + '.html'), encoding='utf-8').read())
    title = soup.title.get_text(strip=True) if soup.title else name
    parts = []
    for sec in soup.select('main section.page-section'):
        a = section_attrs(sec)
        if 'content-collection' in sec.get('class', []):
            parts.append('<!-- collection-list -->')
            continue
        if 'gallery-section' in sec.get('class', []):
            parts.append(section_open(a, 'section-gallery') + '\n<div class="section-inner">\n'
                         + convert_gallery_section(sec) + '\n</div>\n</section>')
            continue
        lay = sec.select_one('.sqs-layout')
        body = layout_html(lay) if lay else ''
        fe = sec.select_one('.fluid-engine')
        if fe and not lay:
            # newer Squarespace grid ("Fluid Engine"): stack its blocks in document order
            body = '\n'.join(h for blk in fe.select('.fe-block > .sqs-block') if (h := convert_block(blk)) and (h := wrap_block(blk, h)))
            a.setdefault('content', 'medium')
            a['content'] = 'medium' if a['content'] == 'wide' else a['content']
        parts.append(section_open(a) + '\n<div class="section-inner">\n' + body + '\n</div>\n</section>')
    first = soup.select_one('main section.page-section')
    header_theme = (first.get('data-section-theme') if first else '') or 'white'
    desc = soup.find('meta', attrs={'name': 'description'})
    convert_page.description = (desc.get('content') or '').strip() if desc else ''
    return title, header_theme, '\n\n'.join(parts)


def fmt_date(ms):
    # site time zone is US/Michigan; Squarespace shows dates in that zone
    d = datetime.fromtimestamp(ms / 1000, tz=timezone.utc).astimezone(ZoneInfo('US/Michigan'))
    return d.strftime('%Y-%m-%d')


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)


def meta_comment(d):
    return '<!--meta\n' + json.dumps(d, ensure_ascii=False, indent=2) + '\n-->\n'


def load_collection(col):
    """Collection JSON plus all its items. Squarespace returns 20 items per request, so follow
    pagination.nextPageUrl; each further page is cached as original/<col>-p<N>.json."""
    js = json.load(open(os.path.join(ORIG, col + '.json'), encoding='utf-8'))
    items = list(js['items'])
    page, cur = 2, js
    while (cur.get('pagination') or {}).get('nextPage'):
        path = os.path.join(ORIG, '%s-p%d.json' % (col, page))
        if not os.path.exists(path):
            url = HOST + cur['pagination']['nextPageUrl'] + '&format=json-pretty'
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                open(path, 'wb').write(r.read())
        cur = json.load(open(path, encoding='utf-8'))
        items.extend(cur['items'])
        page += 1
    return js, items


def main():
    # plain pages and the top part of collection pages
    for name in PLAIN + COLLECTIONS:
        title, header_theme, body = convert_page(name)
        title = title.split(' — ')[0] if ' — ' in title else title
        meta = {'title': re.sub(r'\s+\d+$', '', title), 'header': header_theme}
        if convert_page.description:   # SEO / share description set in Squarespace
            meta['description'] = convert_page.description
        if name in COLLECTIONS:
            js, _ = load_collection(name)
            meta['collection'] = name
            meta['list'] = js['collection'].get('typeName', 'blog-masonry')
            if js['collection'].get('categories'):
                meta['categories'] = js['collection']['categories']
        if not body.strip():   # empty Squarespace page: keep its empty area so the footer sits where it does live
            body = '<section class="section theme-white empty-page"></section>'
        write(os.path.join(SRC, 'pages', name + '.html'), meta_comment(meta) + body + '\n')
        print('page', name, len(body))

    # posts
    for col in COLLECTIONS:
        js, items = load_collection(col)
        for order, it in enumerate(items):
            soup = soupify(it['body'])
            lay = soup.select_one('.sqs-layout')
            body = layout_html(lay) if lay else ''
            exc = soupify(it.get('excerpt') or '')
            exc_html = clean_text_html(exc.body) if exc.body else ''
            meta = {
                'title': it['title'].strip(),
                'date': fmt_date(it.get('publishOn') or it.get('addedOn')),
                'order': order,
                'thumbnail': asset(it.get('assetUrl')),
                'excerpt': exc_html,
            }
            if it.get('categories'):
                meta['categories'] = it['categories']
            write(os.path.join(SRC, 'posts', col, it['urlId'] + '.html'), meta_comment(meta) + body + '\n')
        print('posts', col, len(items))

    # footer
    s = open(os.path.join(ORIG, 'index.html'), encoding='utf-8').read()
    soup = soupify(s)
    foot = soup.select_one('footer .sqs-layout')
    write(os.path.join(SRC, 'footer.html'), layout_html(foot) + '\n' if foot else '')

    fetch_all()
    json.dump(downloads, open(os.path.join(SRC, 'asset-map.json'), 'w', encoding='utf-8'), indent=1)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
