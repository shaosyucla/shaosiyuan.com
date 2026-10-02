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
| Test address | `https://shaosyucla.github.io/shaosiyuan.com/` now redirects to the live domain. Actions workflow publishes `site/` on every push to `main` (live in about 1 minute) |
| Domain | `shaosiyuan.com` at Squarespace Domains, renews 2027-09-16, auto-renew ON. DNS points to GitHub Pages since 2026-10-01 (section 1a) |
| Live | Since 2026-10-02 02:45 PDT `https://www.shaosiyuan.com` is served by GitHub Pages: custom domain set, Let's Encrypt certificate for www + apex (GitHub renews it), Enforce HTTPS on; http, `shaosiyuan.com` and the old test address all redirect there. url_test 190/190 on the live domain. Squarespace website plan kept as the undo until about mid-October, then cancel the website plan only (not the domain) |

## 1a. DNS (Squarespace → Domains → shaosiyuan.com → DNS → DNS Settings)

Records BEFORE the switch (owner's screenshot and public DNS lookup, 2026-10-01). Keep this table: it is the undo.

| Section | Type | Name | TTL | Data |
|---|---|---|---|---|
| Preset "Squarespace Defaults" | A | @ | 4 hrs | 198.185.159.144 |
| | A | @ | 4 hrs | 198.185.159.145 |
| | A | @ | 4 hrs | 198.49.23.144 |
| | A | @ | 4 hrs | 198.49.23.145 |
| | CNAME | www | 4 hrs | ext-sq.squarespace.com |
| Preset "Squarespace Domain Connect" | CNAME | _domainconnect | 1 hr | _domainconnect.domains.squarespace.com (shown shortened) |
| Custom records | TXT | _github-pages-challenge-shaosyucla | 4 hrs | 530dbc4f0c5803c5dc7fb8f6b67093 (GitHub domain verification) |

No MX records: the domain has no email, so nothing mail-related can break. Name servers: Squarespace (ns01–04.squarespacedns.com) and NS1 (dns1–4.p05.nsone.net).

Records AFTER the switch (GitHub Pages):

| Section | Type | Name | Data |
|---|---|---|---|
| Custom records (ADD RECORD) | A | @ | 185.199.108.153 |
| | A | @ | 185.199.109.153 |
| | A | @ | 185.199.110.153 |
| | A | @ | 185.199.111.153 |
| | CNAME | www | shaosyucla.github.io |
| optional (IPv6) | AAAA | @ | 2606:50c0:8000::153, 2606:50c0:8001::153, 2606:50c0:8002::153, 2606:50c0:8003::153 |
| keep | TXT | _github-pages-challenge-shaosyucla | (unchanged) |
| keep | preset | Squarespace Domain Connect | (unchanged; lets Squarespace manage the domain) |

Order: add the 4 A records (ADD RECORD) → delete the "Squarespace Defaults" preset (trash icon) → add the `www` CNAME.
A name can hold only one CNAME, so the `www` record can only go in after the defaults are gone. Do not leave both sets
of A records: visitors would land on either host at random and GitHub's certificate check fails.
Old answers stay cached up to the 4-hour TTL; both sites look the same, so that is harmless.

ADD PRESET has no GitHub entry (its list: Squarespace defaults, Squarespace domain connect, Squarespace Email Campaigns,
Google Workspace, Titan, Zoho, Fastmail, Proton, Neo, iCloud Mail, Google Workspace verification, Vercel, Railway,
Netlify), so the GitHub records go in through ADD RECORD. "Squarespace defaults" is greyed out while it is installed.

Certificate trap (2026-10-01/02): after the DNS switch GitHub's checker kept the old `www` CNAME for the full 4-hour
TTL, then reported both names eligible but never requested a certificate (no `https_certificate` in
`gh api repos/shaosyucla/shaosiyuan.com/pages`). Fix: remove and re-add the custom domain
(`echo '{"cname": null}' | gh api -X PUT repos/shaosyucla/shaosiyuan.com/pages --input -`, then
`gh api -X PUT repos/shaosyucla/shaosiyuan.com/pages -f cname=www.shaosiyuan.com`): the certificate was approved within
a minute. Then `gh api -X PUT repos/shaosyucla/shaosiyuan.com/pages -F https_enforced=true`. Re-saving the same value
does not trigger it.

Undo: delete the GitHub A/AAAA records and the `www` CNAME, then ADD PRESET → Squarespace defaults (or add the five
records in the BEFORE table by hand). Works while the Squarespace website plan is still active.

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
6. `python tools\build.py` (also writes `sitemap.xml` and `robots.txt`; hidden pages go in `site.json`
   `"sitemapExclude"`), then `python tools\check_links.py`, preview, commit, push.

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
- Page gutter 4vw (6vw on phones). First section adds the header height.
- Section padding is in VMAX (the longer window side, so portrait phones and tablets use the HEIGHT), from
  `.page-section.vertical-alignment--middle.section-height--small|medium|large > .content-wrapper`:
  small 3.3vmax, medium 6.6vmax, large 10vmax; custom height N vh → `calc(N vmax / 10)` (inline on the live section;
  the copy sets `--section-pad` inline, e.g. 9vmax for the 90vh heroes, 1vmax via `.height-custom`).
  Bottom-aligned: top doubled (13.2vmax for medium), bottom `--pagePadding` 4vw. Top-aligned: the reverse.
  Gallery and collection sections are excluded (their own padding).
- Footer = small section: 3.3vmax plus the block's 17px on phones (0 on wider screens); min-height 33vh.
- Short pages: the footer sits at the bottom of the window (site wrapper min-height 100vh; the copy uses a flex body).
- Lists (`.blog-masonry`, `.blog-basic-grid`): padding `--pagePadding` = 4vw top and bottom, sides 4vw (6vw on phones).
- Post end: `.blog-item-content` margin-bottom 3vw + article padding = gutter (4vw; 6vw on phones).
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
- PHONES (<768px): every block keeps 17px top AND bottom
  (`@media (max-width:767px) .sqs-layout .sqs-row .sqs-block:first-child/:last-child {padding:17px !important}`).
  The copy: `main .blk { padding-top/bottom: 17px !important }`. Spacer blocks are hidden on phones
  (`.sqs-layout .spacer-block {display:none}`). Uneven columns (`span-x`, inline width) stack full width.
- Fluid Engine blocks (only `/introduction-to-password`): no block padding; on phones the block spans N grid rows
  of min 24px with 11px gaps (`--fe-min-mobile`).

### Breakpoints
- Menu button header: below 800px. Columns stack, phone type and spacing: below 768px.
- Live site keeps the desktop menu and two-column layouts on tablets 800–1024px.
- Life gallery: 3 columns above 768px, 2 columns at 768px and below. Gap = 4.6vw, stepped down to 3.45vw (≤991px),
  2.3vw (≤768px), 1.15vw (≤575px). Captions 14px, padding 15px 0, caption paragraph margin 0
  (`.gallery-caption p.gallery-caption-content { margin:0 }`). Gallery section padding = page gutter.
- Blog masonry: 2 columns, 18px gap (1 column and 5px on phones; meta-to-title and excerpt-to-Read-More 2vw on phones).
- Basic grid (Moments Mechanical): width `1200px - 8vw`, column gap 60px, row gap 65px (phones: no grid, 30px item margin).

### Blocks
- Image: caption body size (or `small` 16px), 16px below the image, caption paragraph keeps 16px bottom margin.
  Crop box = `aspect-ratio` from Squarespace's `padding-bottom %`; focal point CENTRED in the box (site.js, `data-focal`).
  Small images keep their own width (`figure style="max-width:Npx"`) and are centred.
- Section background images: focal point as PERCENTAGE (`object-position: fx% fy%`) — a different formula from image blocks.
- Collage (photo + grey card): photo 60% wide, card 50% wide, overlap 10%, card padding 5% of the block, background
  #e0e0db, card centred against the photo, 15px between card paragraphs.
  Narrow rule (Squarespace script: `.image-block-outer-wrapper` `offsetWidth < 415` → `sqs-narrow-width`, on load and
  resize): the BLOCK width decides, not the window. Stacked: photo 90% wide at its own aspect ratio, card 90% wide pulled
  up by 20% of the block (`margin-top: calc(-10% - 10%)`), card padding 10% of the card. Photo left → card on the right;
  photo right → photo shifted 10% right, card on the left. site.js adds `.narrow` the same way. Half-width collages
  stack on tablets (768–1024px) while full-width ones stay side by side on phones wider than about 470px.
- Float blocks: width = span / parent-column-span of the column, image inset 17px, 17px margin on the text side.
- Quote: body font at the large size, `margin: 1em 0`, source right-aligned in Poppins 16px.
- Horizontal rule: 1px black, 9.5px margin. Gallery block: gap = its JSON `padding` (50px) plus one gap below.
- Video with custom thumbnail: thumbnail + white play triangle; click loads the player with `autoplay=1`.
- Text: `white-space: pre-wrap` (keeps runs of spaces and line breaks); long URLs `overflow-wrap: break-word`.
  Empty paragraph = one blank line (`p.blank`). Underlined spans → `<u>`. Indented paragraphs keep `margin-left`.
- Read More link: 1px line under the text box (not a text underline). Category label before the date on cards
  (card meta then is one line of body font × 1.8, the parent's strut: 31.7px on phones, 34.3px at 1280).
  Post pages: category + date in a 16px flex row (title 32px below; 20px on phones).
- Blog cards: masonry thumbnails are sized by Squarespace's script to `floor(round(column width) × ratio) + 1` px
  (site.js does the same); thumbnail margin 20px (5vw on phones); meta margin 20px (2vw on phones); Read More 20px
  above (2vw on phones). Basic grid: no grid on phones, items `margin-bottom: 30px`; thumbnail box
  `padding-bottom: 66.666%` measures 1px taller (`calc(66.666% + 1px)`).

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
| `python tools\drift_test.py <base> --device "iPhone 17 Pro"` (or `--width 1280`, `--device "iPad Mini"`, `--skip-live`, `p=/path`) | every heading/paragraph matched by text on both sites: drift, page height, and spacing errors with line-wrap (font) differences removed; `compare\drift\report_<setup>.txt` |
| `python tools\measure_collage.py`, `measure_gallery.py` | collage boxes at 14 widths; every Life gallery item by caption |

After the DNS switch (2026-10-02) `https://www.shaosiyuan.com` IS the copy. url_test (saved live titles) and
clickthrough `--skip-live` (saved live results) and drift_test `--skip-live` (`compare\drift\live_*.json`) still
compare against Squarespace; matrix_test has no cache, so its "live" side is now the copy itself. Preview
changes locally with serve.py before pushing: every push goes live.

Visual review that converged: 7 reviewer agents read the side-by-side slices, 1 synthesizer groups the findings and
re-checks examples. About 1.2M subagent tokens per full round; round results: 1 → 24 → 75 of 93 pages identical.

Latest results (commit 1ef432b on the test address, 2026-10-01): url_test 190/190, clicks 37/37, pages 88/89 (contact
map), device matrix 83/96 (all 13 left are script errors inside Vimeo's bot-check frame and the Google map; no layout
differences). Drift test, spacing between texts within 6px: iPhone 83/89, 1280 84/89, iPad Mini 82/89; every page left
is a font line wrap, a live load-timing quirk, or a cross-column comparison (section 8).

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
- A value tuned on ONE device hides a missing rule: 14.3vw section padding matched 375×812 only because it equals
  6.6vmax there; a 26.8px footer padding was 3.3vmax at 812px height. When a phone value looks odd, look for vmax/vh.
- Old compensation rules must go when the real rule lands (the stacked-column 17px rule double-counted once every
  block kept 17px on phones). Re-run the drift test on every device after each rule.
- `figure:not(.collage) figcaption p` (0,1,3) beats `.gallery-section figcaption p` (0,1,2): count `:not()` classes.
- The live site has broken characters in some titles (U+FFFD); the drift test compares texts with non-ASCII as `?`.
- Measure text lines, not element boxes: padding inside vs margin outside moves the box but not the text.
- Most remaining phone height differences are line wraps (EB Garamond vs Adobe Garamond Pro), ±32px per line.

## 8. Open differences

Fixed in round 4 (2026-10-01, commit 1ef432b): collage stacking (block < 415px), Life gallery caption margin, card
titles `h1`, Moments Mechanical grid, short pages' footer, all phone/tablet section and block spacing.

Still open:
1. Contact map: standard Google embed in grayscale vs Squarespace's styled map (needs Squarespace's map key).
2. Body font (licence), browser-tab icon (live shows Squarespace's default), `/success` left out (owner decisions).
3. Line wraps: EB Garamond and Adobe Garamond Pro break lines in different places, so some paragraphs are one line
   (about 32px on phones) longer or shorter. Long posts on phones end up to about 160px apart in height while every
   spacing matches. Only the licensed font removes this.
4. Not rules, not copied: Squarespace's masonry sometimes measures a card before the web font loads (a 41px gap on
   Life Blog phones); its scroll-in animation draws a card about 15px low until it finishes.
