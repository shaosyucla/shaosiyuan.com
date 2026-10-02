"""Local preview server that answers like GitHub Pages:
  /about          -> about.html          (addresses without .html, as on Squarespace)
  /life-blog      -> life-blog/ folder index, else life-blog.html
  missing address -> 404.html with status 404

    python serve.py            # http://127.0.0.1:8791
    python serve.py 8792       # other port
"""
import http.server
import os
import sys
import urllib.parse

SITE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'site')


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=SITE, **kw)

    def send_head(self):
        parts = urllib.parse.urlsplit(self.path)
        fs = self.translate_path(parts.path)
        if not os.path.exists(fs) and os.path.isfile(fs + '.html'):
            self.path = urllib.parse.urlunsplit(parts._replace(path=parts.path + '.html'))
        return super().send_head()

    def send_error(self, code, message=None, explain=None):
        page = os.path.join(SITE, '404.html')
        if code == 404 and os.path.isfile(page):
            body = open(page, 'rb').read()
            self.send_response(404)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(body)
            return
        super().send_error(code, message, explain)

    def log_message(self, fmt, *args):
        pass  # quiet


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8791
    print('serving %s at http://127.0.0.1:%d' % (os.path.abspath(SITE), port))
    http.server.ThreadingHTTPServer(('127.0.0.1', port), Handler).serve_forever()
