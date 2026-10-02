"""Search the live Squarespace stylesheet (original/live_site.css) for rules whose selector contains a pattern.

    python grep_live_css.py image-caption-wrapper blog-more-link ...
Prints selector { body } for rules that set spacing/size properties. Media-query context is shown.
"""
import os, re, sys

CSS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'original', 'live_site.css')
PROPS = re.compile(r'margin|padding|max-width|width|height|border|line-height|gap|underline|bottom|top|font-size|background')


def rules(css):
    """Yield (media, selector, body) by walking braces once (linear time)."""
    stack, buf = [], ''
    for ch in css:
        if ch == '{':
            stack.append(buf.strip()); buf = ''
        elif ch == '}':
            if stack:
                sel = stack.pop()
                if not sel.startswith('@'):
                    media = ' '.join(s for s in stack if s.startswith('@'))
                    yield media, sel, buf.strip()
            buf = ''
        else:
            buf += ch


def main():
    css = open(CSS, encoding='utf-8', errors='replace').read()
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    pats = sys.argv[1:]
    found = {p: [] for p in pats}
    for media, sel, body in rules(css):
        for p in pats:
            if p in sel and PROPS.search(body):
                found[p].append((media, sel, body))
    for p in pats:
        print('### %s (%d)' % (p, len(found[p])))
        for media, sel, body in found[p][:10]:
            print('   %s%s { %s }' % ('[' + media[:40] + '] ' if media else '', sel[-180:], body[:220]))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
