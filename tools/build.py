"""Build the static site: ..\\src  ->  ..\\site

    python build.py

src/layout.html      page template (header, nav, footer slots)
src/site.json        site title, navigation, date formats
src/footer.html      footer content
src/pages/*.html     one file per top-level page (meta comment + sections)
src/posts/<collection>/<slug>.html   blog posts (meta comment + body)

site/css, site/js, site/img, site/files are edited in place; build.py only writes the .html files.
Links and image paths in src are written root-relative ("/about.html", "/img/x.jpg");
the build makes them relative so the site works from a folder, file://, or any host.
"""
import html as htmllib
import json
import os
import re
import sys
import urllib.parse
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'src')
SITE = os.path.join(ROOT, 'site')
# thin chevrons, same shape as Squarespace's caret icons (viewBox 9x16)
CHEV_RIGHT = ('<svg class="chev" viewBox="0 0 9 16" aria-hidden="true">'
              '<polyline fill="none" stroke="currentColor" stroke-miterlimit="10" points="1.6,1.2 6.5,7.9 1.6,14.7"/></svg>')
CHEV_LEFT = ('<svg class="chev" viewBox="0 0 9 16" aria-hidden="true">'
             '<polyline fill="none" stroke="currentColor" stroke-miterlimit="10" points="7.4,1.2 2.5,7.9 7.4,14.7"/></svg>')
MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
META = re.compile(r'^\s*<!--meta\s*(\{.*?\})\s*-->\s*', re.S)


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)


def parse(path):
    text = read(path)
    m = META.match(text)
    meta = json.loads(m.group(1)) if m else {}
    return meta, text[m.end():] if m else text


def fmt(iso, pattern):
    d = date.fromisoformat(iso)
    return pattern.format(d=d.day, m=d.month, yy='%02d' % (d.year % 100), yyyy=d.year,
                          Mon=MONTHS[d.month - 1])


def page_url(path):
    """Squarespace-style address for a page link: '/about.html' -> '/about', '/index.html' -> '/'.
    Files (/img, /files, /css, /js) keep their names. GitHub Pages serves /about from about.html."""
    path, hash_, frag = path.partition('#')
    if not path.startswith(('/img/', '/s/', '/files/', '/css/', '/js/')) and path.endswith('.html'):
        path = path[:-5]
        if path == '/index' or path.endswith('/index'):
            path = path[:-5] or '/'
    return path + hash_ + frag


def relativize(page_html, depth, root_paths=False):
    """Make root paths ("/about.html") relative to a page `depth` folders deep and drop .html from
    page links. With root_paths=True (404 page, served at any depth) links stay root-absolute."""
    prefix = '../' * depth

    def sub(m):
        attr, path = m.group(1), page_url('/' + m.group(2))
        if root_paths:
            return '%s="%s"' % (attr, path)
        rel = prefix + path.lstrip('/')
        return '%s="%s"' % (attr, rel or './')
    return re.sub(r'\b(href|src)="/(?!/)([^"]*)"', sub, page_html)


def image_size_attr(site_path):
    """width/height attributes read from the local image file (lets the masonry lay out before load)."""
    try:
        from PIL import Image
        with Image.open(os.path.join(SITE, site_path.lstrip('/').replace('/', os.sep))) as im:
            return ' width="%d" height="%d"' % im.size
    except Exception:  # noqa: BLE001
        return ''


def cat_file(text):
    """Category file name as Squarespace spells the address: 'Mini Project & Fast Prototype' ->
    'Mini+Project+&+Fast+Prototype' (link form: 'Mini+Project+%26+Fast+Prototype')."""
    return text.replace(' ', '+')


def cat_href(text):
    return urllib.parse.quote(cat_file(text), safe='+')


def text_of(fragment, limit=160):
    t = re.sub(r'<[^>]+>', ' ', fragment)
    t = re.sub(r'\s+', ' ', htmllib.unescape(t)).strip()
    return t[:limit]


class Site:
    def __init__(self):
        self.cfg = json.loads(read(os.path.join(SRC, 'site.json')))
        self.layout = read(os.path.join(SRC, 'layout.html'))
        self.footer = read(os.path.join(SRC, 'footer.html'))
        self.written = 0

    def nav_html(self, active):
        items = []
        for it in self.cfg['nav']:
            cls = ' class="active"' if it['href'] == active else ''
            items.append('    <a href="%s"%s>%s</a>' % (it['href'], cls, it['label']))
        return '\n'.join(items)

    def meta_tags(self, out_rel, full_title, description, image, og_type):
        """canonical + Open Graph / Twitter tags (link previews in chat apps and social media)."""
        site = self.cfg.get('siteUrl', '').rstrip('/')
        path = '/' + re.sub(r'(^|/)index\.html$', '', out_rel)
        path = re.sub(r'\.html$', '', path)
        esc = lambda s: htmllib.escape(s, quote=True)  # noqa: E731
        tags = ['<link rel="canonical" href="%s%s">' % (site, path),
                '<meta property="og:site_name" content="%s">' % esc(self.cfg['siteTitle']),
                '<meta property="og:title" content="%s">' % esc(full_title),
                '<meta property="og:url" content="%s%s">' % (site, path),
                '<meta property="og:type" content="%s">' % og_type,
                '<meta name="twitter:card" content="summary">',
                '<meta name="twitter:title" content="%s">' % esc(full_title)]
        if description:
            tags += ['<meta property="og:description" content="%s">' % esc(description),
                     '<meta name="twitter:description" content="%s">' % esc(description)]
        if image:
            tags += ['<meta property="og:image" content="%s%s">' % (site, image),
                     '<meta name="twitter:image" content="%s%s">' % (site, image)]
        return '\n'.join(tags)

    def render(self, out_rel, title, content, header, active, body_class, description='', image='',
               og_type='website'):
        page = self.layout
        full_title = title if title == self.cfg['siteTitle'] or '|' in title else '%s — %s' % (title, self.cfg['siteTitle'])
        repl = {
            'title': htmllib.escape(full_title, quote=False),
            'description': htmllib.escape(description, quote=True),
            'metaTags': self.meta_tags(out_rel, full_title, description, image, og_type),
            'bodyClass': body_class,
            'headerTheme': header,
            'siteTitle': self.cfg['siteTitle'],
            'nav': self.nav_html(active),
            'content': content,
            'footer': self.footer,
        }
        page = re.sub(r'\{\{(\w+)\}\}', lambda m: repl.get(m.group(1), m.group(0)), page)
        # the 404 page is served at any depth, so it keeps root paths ("/css/site.css")
        write(os.path.join(SITE, out_rel.replace('/', os.sep)),
              relativize(page, out_rel.count('/'), root_paths=(out_rel == '404.html')))
        # same page as <name>/index.html, so the address also works with a trailing slash (/about/)
        if out_rel not in ('index.html', '404.html') and not out_rel.endswith('/index.html'):
            alt = out_rel[:-5] + '/index.html'
            write(os.path.join(SITE, alt.replace('/', os.sep)), relativize(page, alt.count('/')))
        self.written += 1

    def categories_html(self, p, cls):
        """Category links shown before the date (Squarespace "primary meta: categories")."""
        cats = p.get('categories') or []
        col = p['href'].split('/')[1]
        return ''.join('<a class="%s" href="/%s/category/%s.html">%s</a>' % (cls, col, cat_href(c), htmllib.escape(c))
                       for c in cats)

    def posts(self, col):
        folder = os.path.join(SRC, 'posts', col)
        items = []
        for f in sorted(os.listdir(folder)):
            if f.endswith('.html'):
                meta, body = parse(os.path.join(folder, f))
                meta['slug'] = f[:-5]
                meta['body'] = body
                meta['href'] = '/%s/%s.html' % (col, meta['slug'])
                items.append(meta)
        # explicit "order" first (0 = newest, shown first); otherwise newest date first
        items.sort(key=lambda m: m['date'], reverse=True)
        items.sort(key=lambda m: m.get('order', 10 ** 6))
        return items

    def list_html(self, posts, kind, pager=''):
        cards = []
        for p in posts:
            thumb = ''
            if p.get('thumbnail'):
                thumb = '<a class="card-thumb" href="%s"><img src="%s" alt=""%s loading="lazy"></a>' % (
                    p['href'], p['thumbnail'], image_size_attr(p['thumbnail']))
            cards.append('''  <article class="card">
    %s
    <div class="card-meta%s">%s<time class="card-date" datetime="%s">%s</time></div>
    <h1 class="card-title"><a href="%s">%s</a></h1>
    <div class="card-excerpt">%s</div>
    <a class="card-more" href="%s">Read More</a>
  </article>''' % (thumb, ' has-cats' if p.get('categories') else '', self.categories_html(p, 'card-cat'), p['date'], fmt(p['date'], self.cfg['listDateFormat']),
                   p['href'], htmllib.escape(p['title'], quote=False), p.get('excerpt', ''), p['href']))
        cls = 'masonry" data-masonry="2' if 'masonry' in kind else 'grid'
        if not posts:   # empty list (category without posts): Squarespace keeps an empty area
            return '<section class="section blog-list empty"></section>'
        return '<section class="section blog-list">\n<div class="cards %s">\n%s\n</div>\n%s</section>' % (
            cls, '\n'.join(cards), pager)

    def clean(self):
        """Remove every generated .html in site/ (all of them come from src/), so renamed pages leave no stale copies."""
        for dirpath, dirs, files in os.walk(SITE):
            dirs[:] = [d for d in dirs if d not in ('img', 's', 'files', 'css', 'js')]
            for f in files:
                if f.endswith('.html'):
                    os.remove(os.path.join(dirpath, f))

    def build(self):
        self.clean()
        pages_dir = os.path.join(SRC, 'pages')
        for f in sorted(os.listdir(pages_dir)):
            if not f.endswith('.html'):
                continue
            name = f[:-5]
            meta, body = parse(os.path.join(pages_dir, f))
            href = '/%s.html' % name
            col = meta.get('collection')
            if not col:
                self.render('%s.html' % name, meta.get('title', name), body, meta.get('header', 'white'),
                            href, 'is-page page-' + name, meta.get('description') or text_of(body))
                continue
            posts = self.posts(col)
            self.build_posts(col, posts, meta['title'], href)
            self.build_list_pages(name, meta, body, posts, href)
        for alias, target in self.cfg.get('aliases', {}).items():
            self.redirect(alias, target)
        print('wrote %d pages into %s' % (self.written, SITE))

    def build_list_pages(self, name, meta, body, posts, href):
        """Collection page split into pages of postsPerPage (page 1 = /<name>.html,
        page N = /<name>/page-N.html), plus one page per category (/<name>/category/<slug>.html)."""
        per = self.cfg.get('postsPerPage') or len(posts) or 1
        chunks = [posts[i:i + per] for i in range(0, len(posts), per)] or [[]]
        url = lambda n: href if n == 1 else '/%s/page-%d.html' % (name, n)  # noqa: E731
        for n, chunk in enumerate(chunks, 1):
            pager = ''
            if len(chunks) > 1:
                pager = '<nav class="list-pagination">\n'
                pager += (('  <a class="prev" href="%s">' + CHEV_LEFT + '<span>Newer Posts</span></a>\n')
                          % url(n - 1)) if n > 1 else '  <span></span>\n'
                pager += (('  <a class="next" href="%s"><span>Older Posts</span>' + CHEV_RIGHT + '</a>\n')
                          % url(n + 1)) if n < len(chunks) else '  <span></span>\n'
                pager += '</nav>\n'
            page_body = body.replace('<!-- collection-list -->', self.list_html(chunk, meta.get('list', ''), pager))
            outs = [url(n).lstrip('/')]
            if n == 1:
                # same page also as <name>/index.html: GitHub Pages may answer /<name> from the folder
                outs.append('%s/index.html' % name)
            for out in outs:
                self.render(out, meta.get('title', name), page_body, meta.get('header', 'white'), href,
                            'is-page page-' + name, meta.get('description') or text_of(page_body))
        for cat in meta.get('categories', []):
            chosen = [p for p in posts if cat in p.get('categories', [])]
            page_body = body.replace('<!-- collection-list -->', self.list_html(chosen, meta.get('list', '')))
            out = '%s/category/%s.html' % (name, cat_file(cat))
            self.render(out, '%s — %s' % (cat, meta.get('title', name)), page_body, meta.get('header', 'white'),
                        href, 'is-page page-' + name, text_of(page_body))

    def redirect(self, alias, target):
        for out in (alias, alias[:-5] + '/index.html'):   # also with a trailing slash (/home/)
            depth = out.count('/')
            rel = ('../' * depth + page_url(target).lstrip('/')) or './'
            write(os.path.join(SITE, out.replace('/', os.sep)),
                  '<!DOCTYPE html>\n<meta charset="utf-8">\n<title>Redirecting…</title>\n'
                  '<meta http-equiv="refresh" content="0; url=%s">\n<link rel="canonical" href="%s">\n'
                  '<a href="%s">%s</a>\n' % (rel, rel, rel, rel))
        self.written += 1

    def build_posts(self, col, posts, col_title, col_href):
        for i, p in enumerate(posts):
            newer = posts[i - 1] if i > 0 else None
            older = posts[i + 1] if i + 1 < len(posts) else None
            pag = '<nav class="post-pagination">\n'
            pag += (('  <a class="prev" href="%s">' + CHEV_LEFT + '<span class="pag-title">%s</span></a>\n')
                    % (newer['href'], htmllib.escape(newer['title'], quote=False))) if newer else '  <span></span>\n'
            pag += (('  <a class="next" href="%s"><span class="pag-title">%s</span>' + CHEV_RIGHT + '</a>\n')
                    % (older['href'], htmllib.escape(older['title'], quote=False))) if older else '  <span></span>\n'
            pag += '</nav>'
            content = '''<article class="post">
<div class="post-top">
  <div class="post-meta%s">%s<time class="post-date" datetime="%s">%s</time></div>
  <h1 class="post-title">%s</h1>
</div>
<div class="post-body">
%s
</div>
</article>
%s''' % (' has-cats' if p.get('categories') else '', self.categories_html(p, 'post-cat'), p['date'], fmt(p['date'], self.cfg['postDateFormat']),
                htmllib.escape(p['title'], quote=False), p['body'].strip(), pag)
            self.render('%s/%s.html' % (col, p['slug']), p.get('seoTitle') or p['title'], content, 'white', col_href,
                        'is-post post-' + col, p.get('description') or text_of(p.get('excerpt') or p['body']),
                        image=p.get('thumbnail', ''), og_type='article')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    Site().build()
