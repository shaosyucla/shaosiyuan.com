# Hand test: copy vs live, by device

Copy (test address): https://shaosyucla.github.io/shaosiyuan.com/
Live (Squarespace): https://www.shaosiyuan.com/

Method: open the same page on both sites in two tabs and switch between them. Same layout, same spacing,
same clicks = pass. No local server is needed; the test address works on any device.

Expected differences (not errors):
- Font: lines break in slightly different places, so a page can be a little longer or shorter.
- Contact map: plain grey Google map.
- Browser-tab icon: none on the copy.
- The password page's "Here" link opens the "Sorry, nothing to see here" page (`/success` is left out).

## 1. Every device: clicks and addresses

1. Home: each image and button opens its section page.
2. Jumping Vehicle → Let Go: the video shows its thumbnail with a play button; tap it and the video plays.
3. Towards Ornithopter: "Older Posts" at the bottom opens page 2. Open Final Tests: 3 videos, photos with grey
   caption cards, arrows at the bottom open the next and previous posts.
4. Life: images fade in as you scroll. Calendar image → "Improved Lifestyle"; building image → "Francois-Xavier
   Bagnoud"; sand image → the password page.
5. Life Blog: the "Music" label on a card opens the Music category page.
6. About: "resume" opens the PDF. Contact: the map shows.
7. Old addresses: type these after the address and check they open the same page as on live:
   `/about`, `/about/`, `/towards-ornithopter/final-tests`, `/life-blog/category/Music`, `/home`.
8. A wrong address (for example `/xyz`) shows the custom "Sorry, nothing to see here" page.

## 2. Computer, wide window (1024px or wider)

1. Menu links across the top; the current page is underlined.
2. Towards Ornithopter, Life Blog: cards in 2 columns. Moments Mechanical: 2-column grid.
3. Life: gallery in 3 columns.
4. Improved Lifestyle: photo and grey card side by side, the card overlapping the photo edge.
5. Final Tests: the two half-width photo + card figures sit side by side too.

## 3. Tablet (iPad), or a window 800–1023px wide

Use a real iPad, or on the computer: Chrome or Edge → F12 → Ctrl+Shift+M → pick "iPad Mini" (or "Responsive"
and type the width) → reload with F5.

1. Menu links still across the top (no menu button).
2. Final Tests: the two half-width photo + card figures now STACK: photo on top, grey card below, overlapping the
   bottom of the photo and shifted to one side.
3. Improved Lifestyle: still side by side (those figures are full width).
4. iPad held upright: section spacing follows the screen height. Compare the space above and below the first text
   on About and Contact.

## 4. Window 768–799px wide (Responsive mode, type 790)

1. A menu button (two lines) replaces the menu links. Tap it: full-screen menu; tap Contact.
2. Columns still side by side (for example the About and Contact layouts).

## 5. Phone (iPhone Safari, or Responsive mode "iPhone 14 Pro Max" / width 400)

1. Menu button top right; it opens the full-screen menu; Contact opens Contact; the X closes it.
2. Swipe left and right on several pages: the page must not move sideways.
3. Columns stack into one column; cards in one column (Towards Ornithopter, Life Blog, Moments Mechanical).
4. Improved Lifestyle and Final Tests: photo + grey card STACK, the card overlapping the photo's bottom,
   alternating left and right.
5. Life: gallery in 2 columns, captions under the images.
6. Let Go: tap the thumbnail; the video plays.
7. Footer links wrap onto several lines, as on live.
8. Turn the phone sideways: the layout changes the same way as live (a wide phone gets the menu links back).
9. Empty pages (for example `/course-projects/category/Health`): the footer sits at the bottom of the screen.
