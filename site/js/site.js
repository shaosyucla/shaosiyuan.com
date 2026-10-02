// Mobile menu toggle
(function () {
  var btn = document.querySelector('.menu-toggle');
  if (btn) {
    btn.addEventListener('click', function () {
      var open = document.body.classList.toggle('menu-open');
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }
})();

// Masonry: any element with data-masonry="N" lays its children out in N columns,
// placing each item in the currently shortest column (same order as Squarespace).
// Phones (<= 767px) get 1 column for blog cards and 2 for galleries.
(function () {
  var lists = Array.prototype.slice.call(document.querySelectorAll('[data-masonry]'));
  if (!lists.length) return;
  var itemsOf = new Map();
  lists.forEach(function (list) { itemsOf.set(list, Array.prototype.slice.call(list.children)); });

  function columnsFor(list) {
    var n = +list.getAttribute('data-masonry') || 2;
    if (n > 2 && window.innerWidth <= 768) return 2;   // Life gallery: 2 columns at 768px and below
    if (window.innerWidth <= 767) return 1;            // blog cards: one column on phones
    return n;
  }

  function layout(force) {
    lists.forEach(function (list) {
      var cols = columnsFor(list);
      if (!force && list.dataset.cols === String(cols)) return;
      list.dataset.cols = String(cols);
      list.classList.add('is-masonry');
      list.innerHTML = '';
      var columns = [];
      for (var i = 0; i < cols; i++) {
        var c = document.createElement('div');
        c.className = 'masonry-col';
        list.appendChild(c);
        columns.push(c);
      }
      // images carry width/height attributes, so heights are known before they load
      itemsOf.get(list).forEach(function (item) {
        var target = columns.reduce(function (a, b) { return b.offsetHeight < a.offsetHeight ? b : a; });
        target.appendChild(item);
      });
    });
  }

  layout(true);
  // caption heights change when the web fonts arrive; place the items again then
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { layout(true); });
  window.addEventListener('resize', function () { layout(false); });
})();

// Video with a custom thumbnail: <div class="video" data-embed="PLAYER URL"><img ...></div>
// Click (or Enter) replaces the thumbnail with the player and starts it.
(function () {
  document.querySelectorAll('.video[data-embed]').forEach(function (box) {
    box.tabIndex = 0;
    box.setAttribute('role', 'button');
    function play() {
      var src = box.getAttribute('data-embed');
      src += (src.indexOf('?') < 0 ? '?' : '&') + 'autoplay=1';
      var f = document.createElement('iframe');
      f.src = src;
      f.title = (box.querySelector('img') || {}).alt || 'Video';
      f.allow = 'autoplay; fullscreen; picture-in-picture';
      f.allowFullscreen = true;
      box.innerHTML = '';
      box.removeAttribute('role');
      box.removeAttribute('data-embed');   // drops the play-triangle overlay (CSS .video[data-embed]::after)
      box.appendChild(f);
    }
    box.addEventListener('click', play, { once: true });
    box.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); play(); } });
  });
})();

// Life gallery: fade each image up when it scrolls into view
(function () {
  var figs = document.querySelectorAll('.gallery-section figure');
  if (!figs.length || !('IntersectionObserver' in window)) return;
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { e.target.classList.add('is-visible'); io.unobserve(e.target); }
    });
  }, { rootMargin: '0px 0px -10% 0px' });
  figs.forEach(function (f) { f.classList.add('fade-up'); io.observe(f); });
})();

// Old Squarespace page-2 address (/towards-ornithopter?offset=...) -> our page 2
(function () {
  var q = location.search;
  if (q.indexOf('offset=') < 0 || q.indexOf('reversePaginate') >= 0) return;
  var next = document.querySelector('.list-pagination .next');
  if (next) location.replace(next.href);
})();

// Cropped images (data-focal="x,y", 0..1): centre the focal point in the box, as Squarespace does.
// CSS object-position % would place the overflow, not the point, so compute pixels here.
(function () {
  var imgs = Array.prototype.slice.call(document.querySelectorAll('img[data-focal]'));
  if (!imgs.length) return;
  function place(img) {
    var f = img.getAttribute('data-focal').split(',');
    var nw = img.naturalWidth, nh = img.naturalHeight, bw = img.clientWidth, bh = img.clientHeight;
    if (!nw || !nh || !bw || !bh) return;
    var s = Math.max(bw / nw, bh / nh), w = nw * s, h = nh * s;
    var x = Math.min(Math.max(+f[0] * w - bw / 2, 0), w - bw);
    var y = Math.min(Math.max(+f[1] * h - bh / 2, 0), h - bh);
    img.style.objectPosition = (-x) + 'px ' + (-y) + 'px';
  }
  imgs.forEach(function (img) {
    if (img.complete) place(img);
    img.addEventListener('load', function () { place(img); });
  });
  window.addEventListener('resize', function () { imgs.forEach(place); });
})();
