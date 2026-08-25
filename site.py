"""Build the installable web app: eight days in one page, plus PWA plumbing.

    python site.py                 -> output/site/
    python site.py --days 8

One HTML file holds every day, with a day picker that toggles between them.
No fetch, no JSON round trip: once the page is open, switching days is instant
and works offline, which is most of what a service worker would otherwise have
to arrange.
"""

import argparse
import json
import os
import struct
import zlib
from datetime import timedelta
from zoneinfo import ZoneInfo

import espn
import race
import render
import sheets
import sports_daily

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "output", "site")

BG = (0x16, 0x16, 0x1A)
FG = (0xE0, 0x83, 0x4F)

APP_CSS = """
.days {
  position: sticky; top: 0; z-index: 5; display: flex; gap: 6px;
  overflow-x: auto; padding: 10px 0 12px; margin: 0 0 18px;
  background: var(--bg); border-bottom: 1px solid var(--line);
  -webkit-overflow-scrolling: touch; scrollbar-width: none;
}
.days::-webkit-scrollbar { display: none; }
.days button {
  flex: 0 0 auto; font: inherit; font-size: 13px; line-height: 1.15;
  padding: 7px 11px; border-radius: 9px; cursor: pointer; text-align: center;
  background: var(--card); color: var(--ink); border: 1px solid var(--line);
}
.days button b { display: block; font-size: 15px; font-weight: 600; }
.days button small { color: var(--muted); font-size: 11px; }
.days button[aria-current="true"] {
  background: var(--accent); border-color: var(--accent); color: #fff;
}
.days button[aria-current="true"] small { color: rgba(255,255,255,.85); }
.day { display: none; }
.day.on { display: block; }
.day > h1 { font-size: 22px; margin: 0 0 2px; }
"""

APP_JS = """
(function () {
  var bar = document.getElementById('days');
  var days = Array.prototype.slice.call(document.querySelectorAll('.day'));
  function show(id) {
    days.forEach(function (d) { d.classList.toggle('on', d.id === id); });
    Array.prototype.forEach.call(bar.children, function (b) {
      b.setAttribute('aria-current', b.dataset.day === id ? 'true' : 'false');
    });
    try { localStorage.setItem('day', id); } catch (e) {}
    window.scrollTo(0, 0);
  }
  bar.addEventListener('click', function (e) {
    var b = e.target.closest('button');
    if (b) { show(b.dataset.day); }
  });
  // Deliberately not restoring the stored day: opening the app should always
  // land on today, which is the whole point of it.
  var first = document.querySelector('.day');
  if (first) { show(first.id); }
  // Swipe between days. Only horizontal gestures count, so a normal vertical
  // scroll never changes the day by accident.
  var x0 = null, y0 = null;
  document.addEventListener('touchstart', function (e) {
    if (e.touches.length !== 1) { x0 = null; return; }
    x0 = e.touches[0].clientX; y0 = e.touches[0].clientY;
  }, { passive: true });
  document.addEventListener('touchend', function (e) {
    if (x0 === null) { return; }
    var dx = e.changedTouches[0].clientX - x0;
    var dy = e.changedTouches[0].clientY - y0;
    x0 = null;
    if (Math.abs(dx) < 60 || Math.abs(dx) < Math.abs(dy) * 1.5) { return; }
    var ids = days.map(function (d) { return d.id; });
    var at = ids.indexOf(document.querySelector('.day.on').id);
    var next = at + (dx < 0 ? 1 : -1);
    if (next >= 0 && next < ids.length) {
      show(ids[next]);
      var btn = bar.children[next];
      if (btn && btn.scrollIntoView) {
        btn.scrollIntoView({ inline: 'center', block: 'nearest' });
      }
    }
  }, { passive: true });

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('sw.js').catch(function () {});
  }
})();
"""

SW_JS = """
/* Network-first for the page so a new build wins, cache as the fallback. */
var CACHE = 'sports-daily-v1';
self.addEventListener('install', function (e) { self.skipWaiting(); });
self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k !== CACHE; })
                           .map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});
self.addEventListener('fetch', function (e) {
  if (e.request.method !== 'GET') { return; }
  e.respondWith(
    fetch(e.request).then(function (res) {
      var copy = res.clone();
      caches.open(CACHE).then(function (c) { c.put(e.request, copy); });
      return res;
    }).catch(function () { return caches.match(e.request); })
  );
});
"""


def _png(size):
    """A flat icon drawn by pixel maths -- no image library on this machine.

    A ring on a dark ground: legible at 48px on a home screen, and it costs
    nothing to generate at every size the manifest wants.
    """
    centre = (size - 1) / 2.0
    outer = size * 0.34
    inner = size * 0.22
    rows = []
    for y in range(size):
        row = bytearray([0])            # filter byte: none
        for x in range(size):
            dx, dy = x - centre, y - centre
            dist = (dx * dx + dy * dy) ** 0.5
            on_ring = inner <= dist <= outer
            # A gap on the diagonal, so it reads as a ring rather than a blob.
            if on_ring and abs(dx - dy) < size * 0.06 and dx > 0:
                on_ring = False
            row += bytes(FG if on_ring else BG)
        rows.append(bytes(row))
    raw = b"".join(rows)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


def build(config, days=8, out=SITE):
    tz = ZoneInfo(config.get("timezone", "America/New_York"))
    today = sports_daily.parse_day(None, tz)
    os.makedirs(out, exist_ok=True)

    race.merge_into(config, today=today)
    # The cloud build owns the games-back history now; nothing depends on a
    # machine at home being switched on.
    for line in sports_daily.record_history(config, today, tz):
        print("  history: %s" % line)
    info = [line for line in (race.status(lg) for lg in config.get("leagues", []))
            if line]

    tabs, panels = [], []
    for offset in range(days):
        day = today + timedelta(days=offset)
        games, _ = sports_daily.collect(config, day, tz)
        today_info = list(info) if offset == 0 else None
        if offset == 0 and espn.FAILURES:
            today_info.append("Some data could not be loaded today: %s"
                              % ", ".join(sorted(espn.FAILURES)))
        body = render.day_body(day, games, config, info=today_info)
        ident = "d%s" % day.isoformat()
        label = "Today" if offset == 0 else day.strftime("%a")
        tabs.append(
            '<button data-day="%s" aria-current="false"><b>%s</b>'
            '<small>%s</small></button>'
            % (ident, label, day.strftime("%b %d").replace(" 0", " ")))
        panels.append(
            '<section class="day" id="%s"><h1>%s</h1>%s</section>'
            % (ident, day.strftime("%A, %B %d").replace(" 0", " "), body))
        print("  %s  %d games" % (day.isoformat(), len(games)))

    page = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,'
        'viewport-fit=cover">'
        '<title>Games</title>'
        '<link rel="manifest" href="manifest.webmanifest">'
        '<meta name="theme-color" content="#16161a">'
        '<meta name="apple-mobile-web-app-capable" content="yes">'
        '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">'
        '<link rel="apple-touch-icon" href="icon-180.png">'
        '<style>%s%s</style></head><body><div class="wrap">'
        '<nav class="days" id="days">%s</nav>%s'
        '<footer>From ESPN. Times in %s.</footer>'
        '</div><script>%s</script></body></html>'
    ) % (render.CSS, APP_CSS, "".join(tabs), "".join(panels),
         config.get("timezone", "local"), APP_JS)

    manifest = {
        "name": "Sports Daily", "short_name": "Games",
        "start_url": ".", "scope": ".", "display": "standalone",
        "background_color": "#16161a", "theme_color": "#16161a",
        "icons": [{"src": "icon-%d.png" % s, "sizes": "%dx%d" % (s, s),
                   "type": "image/png",
                   "purpose": "any maskable"} for s in (192, 512)],
    }

    files = {
        "index.html": page.encode("utf-8"),
        "manifest.webmanifest": json.dumps(manifest, indent=2).encode("utf-8"),
        "sw.js": SW_JS.encode("utf-8"),
        ".nojekyll": b"",           # GitHub Pages must not run Jekyll over this
    }
    for size in (180, 192, 512):
        files["icon-%d.png" % size] = _png(size)

    for name, data in files.items():
        with open(os.path.join(out, name), "wb") as fh:
            fh.write(data)

    # Committed alongside the history, so the workflow's later slot can tell
    # whether the earlier one actually ran.
    stamp_dir = os.path.join(HERE, "output", "history")
    os.makedirs(stamp_dir, exist_ok=True)
    with open(os.path.join(stamp_dir, "_last_build.txt"), "w", encoding="utf-8") as fh:
        fh.write(today.isoformat())
    return out, len(page)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the Sports Daily web app")
    ap.add_argument("--days", type=int, default=15)
    ap.add_argument("--out", default=SITE)
    args = ap.parse_args(argv)

    config = sports_daily.load_config()
    sheets.load(config)
    out, size = build(config, days=args.days, out=args.out)
    print("wrote %s (%.0f KB page)" % (out, size / 1024.0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
