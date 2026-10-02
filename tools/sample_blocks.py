"""Dump one raw example of each block kind (shortened) so the converter can be written against real markup."""
import json, os, re
from bs4 import BeautifulSoup

ORIG = os.path.join(os.path.dirname(__file__), '..', 'original')
seen = {}


def kind_of(b):
    return b.get('data-definition-name') or [c for c in b['class'] if c.endswith('-block') and c != 'sqs-block'][0]


def scan(html):
    soup = BeautifulSoup(html, 'lxml')
    for b in soup.select('div.sqs-block'):
        k = kind_of(b)
        if k == 'image-block' and b.find('figcaption') and 'image-cap' not in seen:
            seen['image-cap'] = str(b)
        if k == 'image-block' and b.find('a') and 'image-link' not in seen:
            seen['image-link'] = str(b)
        seen.setdefault(k, str(b))


for p in ['towards-ornithopter', 'jumping-vehicle', 'moments-mechanical', 'course-projects']:
    for it in json.load(open(os.path.join(ORIG, p + '.json'), encoding='utf-8'))['items']:
        scan(it['body'])
for p in ['index', 'contact']:
    scan(open(os.path.join(ORIG, p + '.html'), encoding='utf-8').read())

for k, v in seen.items():
    v = re.sub(r'<style.*?</style>', '<style/>', v, flags=re.S)
    v = re.sub(r'data-block-(css|scripts)="[^"]*"', '', v)
    v = re.sub(r'\s+', ' ', v)
    print('#####', k, len(v))
    print(v[:2200])
    print()
