# shaosiyuan.com — static rebuild

A plain-HTML copy of the Squarespace site www.shaosiyuan.com, built on 2026-10-01.
Every page reachable on the live site has a page here — 90 pages
(the live `sitemap.xml` lists 72 URLs; a link crawl, `tools/crawl_live.py`, found 19 more):

- 8 menu pages, plus the unlisted `allapplicationdocuments`, `new-page`, `new-page-1` (the last two are empty on the live site too)
  and `introduction-to-password`
- 43 blog posts (Towards Ornithopter has 21, so its list continues on `towards-ornithopter/page-2`, 20 per page as on Squarespace)
- the hidden **Life Blog** (`life-blog`, 12 posts, Hiking/Music category pages) — linked only from Life gallery images
- 17 Course Projects category pages (`course-projects/category/...`) — empty, because no post has a category yet
- `404.html` (custom "page not found") and `home.html`, which redirects to the home page
- Not copied: `/success` is password-protected on Squarespace (decision: leave it out). See `DIFFERENCES.md`.

Page addresses are the same as on Squarespace (`/about`, `/jumping-vehicle/let-go`, `/course-projects/category/ME350`).
Links inside the site have no `.html`; GitHub Pages serves `/about` from `about.html`.
Each blog list page also exists as `<list>/index.html`, so `/towards-ornithopter` works whichever way the host resolves it.

All images and PDFs were downloaded, so the copy does not depend on Squarespace
(one exception: `MATH450.pdf` already returns 404 on the live site).

## Folders

| Folder | What it holds |
|---|---|
| `site/` | **The finished website.** Upload this folder to the web host. |
| `site/css/site.css` | All styling. The values at the end of the file were measured on the live site. |
| `site/js/site.js` | Phone menu, masonry layout, video thumbnails (click to play), focal-point cropping, Life gallery fade-in. |
| `site/img/`, `site/files/` | Downloaded images and PDFs (resume, project overview). |
| `src/pages/*.html` | Page content: home (`index`), about, life, contact, the top part of the blog pages, 404. |
| `src/posts/<blog>/<slug>.html` | One file per blog post. Its first lines hold title, date, thumbnail, excerpt, categories. |
| `src/site.json` | Site title, navigation menu, date formats, posts per page. |
| `src/layout.html`, `src/footer.html` | Header and footer for every page. |
| `tools/build.py` | Turns `src/` into the `.html` files in `site/` (removes old `.html` first). |
| `tools/import_squarespace.py` | One-time importer. **Re-running it overwrites `src/`** and discards edits. |
| `original/` | The raw Squarespace download, crawl list, and the live stylesheet (reference only). |
| `compare/` | Screenshots and test output. |

## Edit loop

1. Edit a file in `src/` (content) or `site/css/site.css` (look).
2. `python tools/build.py`
3. Preview with the server below, at http://127.0.0.1:8792. It answers like GitHub Pages
   (`/about` → `about.html`, missing address → `404.html`).

```
python "C:\FACT Workplace\Numerical Code\Claude Workspace\website\tools\serve.py" 8792
```

Use the server, not a double-click on the file: YouTube refuses to play embeds on `file://` pages.

## Tests

| Command | What it checks |
|---|---|
| `python tools/check_links.py` | Every link and image inside the site points to a file. |
| `python tools/check_parity.py` | Every post has the same words, images and videos as on Squarespace. |
| `python tools/clickthrough.py [url]` | Headless Chrome on the live site and the rebuild: opens every page, clicks menu, home tiles, video thumbnails, Older/Newer Posts, post arrows, Life links, phone menu, 404, old addresses; full-page screenshots. Report: `compare/clickthrough/report.html`. Default `url` is the local server; give the GitHub Pages address to test the published site. `--skip-live` reuses the live results. |
| `python tools/make_review_pairs.py` | Side-by-side images (live left, rebuild right) for visual review: `compare/review/`. |
| `python tools/measure_pairs.py [group]` | Measures the same elements on both sites (position, size, font, spacing). |

## Common edits

- **Video**: in the post, change the URL in `<div class="video" data-embed="...">` (video with a custom thumbnail)
  or in `<iframe src="...">`. YouTube: `https://www.youtube.com/embed/<id>`; Vimeo: `https://player.vimeo.com/video/<id>`.
- **Font**: change `--font-heading` / `--font-body` in `site/css/site.css`, and add the font to the
  Google Fonts link in `src/layout.html`.
- **Text**: edit the paragraph in `src/pages/...` or `src/posts/...`.
- **New post**: copy a post file in `src/posts/<blog>/`, change its meta block and body.
  Set `"order": -1` to show it first in the list (lower `order` = earlier; posts with no `order` go last).
- **Menu**: edit `nav` in `src/site.json`.
- **Posts per list page**: `postsPerPage` in `src/site.json` (set `0` for one long list).
- **Categories**: add `"categories": ["ME350"]` to a post's meta block; the category page lists it.

## Differences from the live site

See `DIFFERENCES.md`.
