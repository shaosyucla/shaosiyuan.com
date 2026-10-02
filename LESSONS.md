# Lessons: rebuilding the Squarespace site www.shaosiyuan.com as a static site

Written 2026-10-01 at the end of the first rebuild. Use it when you add pages or posts, and when you
check the copy against the live Squarespace site. Paths are absolute; the project root is
`C:\FACT Workplace\Numerical Code\Claude Workspace\website`.

## 1. Current state

| Item | State |
|---|---|
| Copy | 90 pages (95 HTML files + `<page>/index.html` twins): 8 menu pages, 3 unlisted pages, `introduction-to-password`, 43 blog posts, hidden Life Blog (12 posts, 2 categories), 17 empty Course Projects categories, Towards Ornithopter page 2, `404.html`, `home` alias |
| Left out | `/success` (password-protected on Squarespace). Owner decision: leave it out |
| Repository | `https://github.com/shaosyucla/shaosiyuan.com` (public). Local clone = the project root |
| Test address | `https://shaosyucla.github.io/shaosiyuan.com/` (GitHub Pages, Actions workflow publishes `site/` on every push to `main`) |
| Domain | `shaosiyuan.com` at Squarespace Domains, renews 2027-09-16, auto-renew ON. GitHub domain verification TXT record added and verified. DNS still points to Squarespace |
| Not done yet | DNS switch, custom domain in GitHub Pages settings, Enforce HTTPS, cancel the Squarespace website plan |

## 2. Project layout and edit loop

- `src/pages/*.html`, `src/posts/<collection>/<slug>.html`: content. Each file starts with a `<!--meta {json} -->`
  block (title, header theme, date, order, thumbnail, excerpt, categories, seoTitle, description).
- `src/site.json` (menu, date formats, `postsPerPage`, `siteUrl`, aliases), `src/layout.html`, `src/footer.html`.
- `site/css/site.css`, `site/js/site.js`, `site/img/`, `site/s/` (PDFs, same path as Squarespace) are edited in place.
- `python tools\build.py` writes all `.html` in `site/` (it deletes old `.html` first).
- `tools\import_squarespace.py` is a ONE-TIME importer. Re-running it overwrites `src/`. Only re-run it before any hand edits.
- Preview: `python tools\serve.py 8792` (answers like GitHub Pages: `/about` → `about.html`, missing → `404.html`).
  Port 8791 may be held by the owner's own hand-test server. Background servers started by Claude stop after 10 minutes.
- Publish: `git add -A`, `git commit`, `git push`. The Actions run takes about 1 minute.

## 3. Adding a page or post later

1. Post: copy an existing file in `src/posts/<collection>/`, change the meta block (`title`, `date`, `thumbnail`,
   `excerpt`; `"order": -1` puts it first; `categories` adds it to category pages; `seoTitle` changes only the tab title).
2. Page: copy `src/pages/about.html` (or another page with the same structure), add a menu entry in `src/site.json`.
3. Write the body with the same building blocks the importer produced (section 5). Wrap every block in
   `<div class="blk blk-<kind>">` so the block spacing rules apply.
4. Images go into `site/img/`, files into `site/s/`. Give `<img>` its `width`/`height` (masonry and layout use them).
5. Video: `<div class="video"><iframe src="https://www.youtube.com/embed/<id>?rel=0" ...></iframe></div>`, or with a
   custom thumbnail `<div class="video" data-embed="<player url>"><img src="/img/<thumb>" alt="Play video: ..."></div>`.
   Non-16:9 video: add `style="aspect-ratio:4/3"` (or the real ratio) to the `.video` div.
6. `python tools\build.py`, then `python tools\check_links.py`, preview, commit, push.

## 4. Squarespace rules reproduced (read from its live site.css and measured)

Copy the RULES, not the pixels: a rule matches on every device; screenshots only check the rules.

### Type (font sizes)
- Desktop and tablet (≥768px): `min(16px + k·vw, cap)`. Cap from `--maxPageWidth: 1200px`:
  `cap = max(16 + 12k, 16 + 16k/1.2)` px. Values: body k=0.24 (19.07px at 1280, cap 19.2), large k=0.6 (cap 24),
  h1 k=3.6 (62.08, cap 64), h2 k=2.16 (cap 44.8), h3 and card titles k=1.44 (cap 35.2), h4 k=0.72 (cap 25.6),
  site title k=1.2 (cap 32).
- Phones (<768px): `16px + k · min(1vh, 9px)` (Squarespace scales phone type with the window HEIGHT).
- Line heights: body 1.8, h1 1.232, h2 1.3, h4 1.366, card title 1.4, post-arrow titles 1.0.
- Fonts: headings Cormorant Garamond 500, body EB Garamond (live: Adobe Garamond Pro, Squarespace licence only),
  dates Poppins 16px.

### Layout widths and spacing
- Page gutter 4vw (6vw on phones). Section padding 6.6vw (14.3vw on phones). First section adds the header height.
- Content max width 1200px; medium sections 75% (max 900px); narrow 50% (max 600px); left-aligned sections start at the
  1200px box edge. Post top and body: `min(75%, 1200px)`.
- Header: padding 3vw (desktop); header height = 6vw + site-title line. Below 800px: menu-button header, padding 6vw,
  button 47×40px, title at body size with line-height 1.2, header height = 12vw + 40px.
- Post page: date 4vw below the header; date-to-title 32px (20px on phones); title-to-body 70px; body-end to arrows
  3vw + 4vw; arrows row padding 3vw; each arrow link max 50% of the row; chevron SVG 9×16 (shown 18×32), 25px gap.
- Blog list "Older / Newer Posts": body font, 9×16 chevron, 12px gap, margins 6vw above and 9vw below.
- 12-column grid: nested rows count spans relative to the parent column (the importer rescales to 12).

### Block model (biggest single source of spacing errors)
- Every block has 17px padding top and bottom, so blocks sit 34px apart; paragraphs inside one text block are 16px apart.
- First block in a column: no top padding. A block alone in its column: no bottom padding either.
- A row that follows a block or another row restores both paddings. Floats keep both.
- Squarespace's own selectors: `.sqs-row .sqs-block:not(.float):first-child {padding-top:0}`,
  `...:first-child:last-child {padding-bottom:0}`, `.sqs-block+.sqs-row ...`, `.sqs-row+.sqs-row ...` restore 17px.

### Breakpoints
- Menu button header: below 800px. Columns stack, phone type and spacing: below 768px.
- Live site keeps the desktop menu and two-column layouts on tablets 800–1024px.
- Life gallery: 3 columns above 768px, 2 columns at 768px and below. Gap = 4.6vw, stepped down to 3.45vw (≤991px),
  2.3vw (≤768px), 1.15vw (≤575px). Captions 14px, padding 15px 0. Gallery section padding = page gutter.
- Blog masonry: 2 columns, 18px gap (5px on phones; card meta-to-title and excerpt-to-Read-More 8px on phones).
- Basic grid (Moments Mechanical): width `1200px - 8vw`, column gap 60px, row gap 65px (29px on phones).

### Blocks
- Image: caption body size (or `small` 16px), 16px below the image, caption paragraph keeps 16px bottom margin.
  Crop box = `aspect-ratio` from Squarespace's `padding-bottom %`; focal point CENTRED in the box (site.js, `data-focal`).
  Small images keep their own width (`figure style="max-width:Npx"`) and are centred.
- Section background images: focal point as PERCENTAGE (`object-position: fx% fy%`) — a different formula from image blocks.
- Collage (photo + grey card): photo 60% wide, card 50% wide, overlap 10%, card padding 5% of the block, background
  #e0e0db, card centred against the photo, 15px between card paragraphs. (Narrow screens: see open items.)
- Float blocks: width = span / parent-column-span of the column, image inset 17px, 17px margin on the text side.
- Quote: body font at the large size, `margin: 1em 0`, source right-aligned in Poppins 16px.
- Horizontal rule: 1px black, 9.5px margin. Gallery block: gap = its JSON `padding` (50px) plus one gap below.
- Video with custom thumbnail: thumbnail + white play triangle; click loads the player with `autoplay=1`.
- Text: `white-space: pre-wrap` (keeps runs of spaces and line breaks); long URLs `overflow-wrap: break-word`.
  Empty paragraph = one blank line (`p.blank`). Underlined spans → `<u>`. Indented paragraphs keep `margin-left`.
- Read More link: 1px line under the text box (not a text underline). Category label before the date on cards
  (card meta then uses body line height).

### Addresses, titles, metadata
- Keep every live address: links without `.html`; each page also as `<page>/index.html` (trailing slash works);
  files at `/s/<name>`; categories as `/<list>/category/<Name>` with `+` for spaces; `/home` redirects home;
  old `?offset=` page-2 links are forwarded by site.js; `404.html` uses root paths.
- Tab titles: the exact live title (`Contact 3`), post SEO titles (`Trout`), categories `<Category> — <List> — Siyuan Shao`.
- Share tags: canonical, Open Graph and Twitter tags with the page description; posts add the thumbnail.

## 5. Importer knowledge (Squarespace markup → clean HTML)

- `?format=json-pretty` on any page gives clean item bodies; collections return 20 items per request — follow
  `pagination.nextPageUrl`.
- `sitemap.xml` MISSES hidden collections and pages. Always crawl links (`tools\crawl_live.py`).
- Block kinds: `website.components.html|image|video|button|quote|horizontalrule|map|spacer`, classic `image-block`,
  `gallery-block`; newer "Fluid Engine" sections use `.fe-block` (stacked in document order).
- Video URL: `data-html` iframe `src`; unwrap Embedly (`?src=`); custom thumbnail in `.sqs-video-overlay img`;
  box shape from `.embed-block-wrapper` `padding-bottom %`.
- BeautifulSoup collapses whitespace-only text; convert runs of spaces to no-break spaces BEFORE parsing, but only in text
  without newlines (template indentation must stay normal whitespace).
- Squarespace serves dates in its site time zone (US/Michigan); use `tzdata` for zoneinfo on Windows.

## 6. Verification (run after every change)

| Command | Checks |
|---|---|
| `python tools\check_links.py` | every local link and image exists (MATH450.pdf and `/success` are the two known misses) |
| `python tools\check_parity.py` | every post: same words, images and videos as the Squarespace source |
| `python tools\url_test.py <base>` | all 190 live addresses (incl. trailing slash and `/s/` files) open the same page (title + status) |
| `python tools\clickthrough.py [--skip-live] <base>` | 89 pages + 37 clicks on live vs copy, full-page screenshots, `compare\clickthrough\report.html` |
| `python tools\matrix_test.py <base>` | Chrome 1920/1366, Edge 1280, Safari engine 1440, iPad Mini, iPhone 17 Pro, iPhone SE, Pixel 7 × 12 pages |
| `python tools\make_review_pairs.py` | side-by-side slices (live left) in `compare\review\` for the visual-review workflow |
| `python tools\measure_pairs.py`, `measure_devices.py`, `measure_live_extra.py` | measure the same elements on both sites |
| `python tools\grep_live_css.py <selector part>` | read Squarespace's exact rule from `original\live_site.css` |

Visual review that converged: 7 reviewer agents read the side-by-side slices, 1 synthesizer groups the findings and
re-checks examples. About 1.2M subagent tokens per full round; round results: 1 → 24 → 75 of 93 pages identical.

Latest results (commit 278c1ff on the test address): url_test 190/190, clicks 37/37, pages 88/89 (contact map),
device matrix 70/96 page checks clean (rest: listed below and third-party script errors from Vimeo/Google frames).

## 7. Traps met

- Git Bash heredoc into Python eats one backslash level: write scripts with the Write tool.
- Git Bash rewrites `/path` arguments into Windows paths: prefix with `MSYS_NO_PATHCONV=1`.
- `sed` with backslashes fails the same way: use the editor.
- Vimeo's bot check answers headless browsers with 401 on both sites: not a site defect.
- Firefox's Playwright build cannot start inside the Claude app sandbox (side-by-side error for `mozglue`).
  Chromium (Chrome, Edge) and WebKit (Safari engine, iPhone/iPad emulation) work. Real iOS Safari is not available.
- The masonry places items by measured height: lay out again after web fonts load, or caption wraps change the order.
- CSS: `.blk > :first-child` beats `.blk > hr`; use `.blk.blk-<kind> > ...` for exceptions.
- Percentage padding of a grid item is taken from its grid-area width, not the block width.
- GitHub Pages folder vs file (`/towards-ornithopter` with both `towards-ornithopter.html` and a folder): write both.

## 8. Open differences (not fixed yet)

1. Collage figures below about 800px: live stacks them (photo about 80–90% wide, grey card overlapping below and
   offset). The copy keeps them side by side down to 768px and stacks without overlap on phones
   (Improved Lifestyle +190px on phones, Final Tests −178px on iPad). Measure the live geometry at 768 and 393px.
2. Life page on phones about 200px taller (gallery caption wrap or item heights; measure).
3. Blog card titles are `h2` in the copy, `h1` on the live site (invisible; SEO only).
4. Contact map: standard Google embed in grayscale vs Squarespace's styled map.
5. Body font (licence), browser-tab icon (live shows Squarespace's default), `/success` left out.
6. Moments Mechanical phone grid: Read More about 9px lower; short pages' footer 3–4px higher.
