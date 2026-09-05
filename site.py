"""Build the installable web app: a fortnight in one page, plus PWA plumbing.

    python site.py                 -> output/site/
    python site.py --days 8

--days counts from today, and yesterday is always added in front of it, so
--days 15 builds 16 tabs. The app still opens on today.

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
from datetime import datetime, timedelta
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
  // The day this page was built for, in the timezone it prints times in.
  var BUILT = '%%BUILT%%';
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
  // land on today, which is the whole point of it. Today is no longer the
  // first panel -- yesterday sits ahead of it -- so it is asked for by name.
  var start_id = 'd' + BUILT;
  var opening = document.getElementById(start_id) || document.querySelector('.day');
  if (opening) {
    show(opening.id);
    var here = bar.querySelector('button[data-day="' + opening.id + '"]');
    // Yesterday is off to the left; bring today into view without moving the
    // page itself.
    if (here && here.scrollIntoView) {
      here.scrollIntoView({ inline: 'center', block: 'nearest' });
      window.scrollTo(0, 0);
    }
  }
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

  // An installed app resumed from the home screen does not reload -- it shows
  // whatever it last rendered, for days, however fresh the server is. So when
  // it comes back into view, reload if the page was built for another day or
  // has simply been sitting a while. BUILT is the day this page was made, in
  // the same timezone the page prints its times in.
  var seen = Date.now();
  function localDay() {
    var now = new Date();
    return new Date(now.getTime() - now.getTimezoneOffset() * 60000)
      .toISOString().slice(0, 10);
  }
  function stale() {
    return localDay() !== BUILT || (Date.now() - seen) > 30 * 60 * 1000;
  }
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') { seen = Date.now(); return; }
    // reload(true) is long gone; a plain reload still revalidates, and the
    // service worker is network-first, so this fetches the current build.
    if (stale()) { location.reload(); }
  });
  // A desktop tab restored from the back/forward cache fires no
  // visibilitychange, so it needs its own hook -- same problem, same test.
  window.addEventListener('pageshow', function (e) {
    if (e.persisted && stale()) { location.reload(); }
  });

  // ---- live scores -------------------------------------------------------
  // ESPN's API sends Access-Control-Allow-Origin: *, so the page can ask it
  // directly, and cache-control: max-age=6 says they expect to be polled. The
  // build sets the slate; this only keeps the numbers current.
  //
  // It can never change WHICH games are listed -- the filters run at build
  // time against standings and odds. Scores and status only.
  var LIVE_MS = 60000;
  var live = null;

  function todayPanel() {
    // The panel for the day this page was built for; nothing else can be
    // live. Not panels[0] any more -- that one is yesterday.
    return document.getElementById('d' + BUILT);
  }

  function rowsToWatch() {
    var panel = todayPanel();
    if (!panel) { return []; }
    return Array.prototype.filter.call(
      panel.querySelectorAll('.row[data-game][data-path]'),
      function (row) { return row.dataset.state !== 'post'; });
  }

  // What a reload paints first is the build's own numbers -- a start time and
  // two records, hours stale by evening -- and the fetch only replaces them a
  // moment later, which reads as a flash of yesterday's page. So the last
  // live state is kept per game and painted back at once on load; the fetch
  // that follows usually just confirms it.
  // Versioned: a stored state is only as good as the fields the code that
  // wrote it knew about, so widening what is remembered retires the old ones
  // rather than trying to interpret them.
  var MEMORY = 'live2:' + BUILT;
  // When the numbers below the date were last confirmed against ESPN. The
  // build writes its own time into the page; every successful poll replaces
  // it, and it is stored so a reload shows the real last update rather than
  // jumping back to 6am.
  var STAMPED = 'updated:' + BUILT;
  var TZ = '%%TZ%%';

  function clockText(ms) {
    try {
      return new Date(ms).toLocaleTimeString('en-US', {
        timeZone: TZ, hour: 'numeric', minute: '2-digit'
      }).replace('AM', 'am').replace('PM', 'pm');
    } catch (e) { return null; }
  }

  function setStamp(ms, store) {
    var el = document.getElementById('updated');
    var text = clockText(ms);
    if (!el || !text) { return; }
    el.textContent = 'Updated ' + text;
    if (!store) { return; }
    try {
      Object.keys(localStorage).forEach(function (k) {
        if (k.indexOf('updated:') === 0 && k !== STAMPED) {
          localStorage.removeItem(k);
        }
      });
      localStorage.setItem(STAMPED, String(ms));
    } catch (e) {}
  }

  var remembered = {};
  try {
    remembered = JSON.parse(localStorage.getItem(MEMORY) || '{}') || {};
  } catch (e) { remembered = {}; }

  function remember(id, st) {
    remembered[id] = st;
    try {
      // Only ever this build's key, so nothing accumulates day after day.
      Object.keys(localStorage).forEach(function (k) {
        if ((k.indexOf('live:') === 0 || k.indexOf('live2:') === 0) && k !== MEMORY) {
          localStorage.removeItem(k);
        }
      });
      localStorage.setItem(MEMORY, JSON.stringify(remembered));
    } catch (e) {}
  }

  // A finished game sinks to the bottom of its card, in the order it
  // started -- the same rule the build sorts by, so a reload changes nothing.
  // Rows are direct children of the card, and the two halves of National are
  // separate cards, so a final never crosses the gap between them.
  function resort(card) {
    var rows = Array.prototype.slice.call(card.children);
    var done = rows.filter(function (r) { return r.dataset.state === 'post'; });
    if (!done.length || done.length === rows.length) { return; }
    done.sort(function (a, b) {
      var x = a.dataset.start || '', y = b.dataset.start || '';
      return x < y ? -1 : x > y ? 1 : 0;
    });
    // Re-appending in order leaves everything still to come untouched and in
    // the order the build gave it.
    done.forEach(function (r) { card.appendChild(r); });
  }

  function applyState(row, st) {
    var when = row.querySelector('.when');
    if (!when) { return; }
    when.textContent = st.text;
    ['home', 'away'].forEach(function (side) {
      var cell = row.querySelector('.s-rec[data-side="' + side + '"]');
      var name = row.querySelector('.t[data-side="' + side + '"]');
      if (cell && st[side] != null && st.state !== 'pre') {
        cell.textContent = st[side];
        cell.classList.add('score');
      }
      // Only when this state has an opinion. A remembered one from before
      // these colours existed carries no `mood` at all, and clearing on that
      // stripped the class the BUILD had put there -- on a finished game,
      // which is never polled again, so it never came back.
      if (cell && st.mood !== undefined) {
        cell.classList.toggle('good', st.mood === 'good');
        cell.classList.toggle('bad', st.mood === 'bad');
      }
      if (name) {
        name.classList.toggle('lost', st.losing === side);
        // A draw has no loser, so both names lean rather than one striking.
        name.classList.toggle('drew', !!st.drawn);
      }
    });
    // ESPN drops the odds node the moment a game is final -- checked over 315
    // finished games, not one kept a spread -- so a build never prints one on
    // a finished game. A page open through the final whistle has to do the
    // same thing itself, or it would sit there showing a line to bet on a
    // game that is over.
    if (st.state === 'post') {
      Array.prototype.forEach.call(row.querySelectorAll('.s-spread'),
        function (el) { el.parentNode.removeChild(el); });
    }
    row.dataset.state = st.state;
    if (st.state === 'post' && row.parentNode) { resort(row.parentNode); }
  }

  // The same rule the build uses: each sport counts its own way, and a delay
  // is worth nothing without saying how far in it got. The league path on the
  // row is enough to tell them apart.
  function periodLabel(path, period) {
    if (!period || period < 1) { return ''; }
    function ord(n) {
      if (n % 100 >= 10 && n % 100 <= 20) { return n + 'th'; }
      return n + ({1: 'st', 2: 'nd', 3: 'rd'}[n % 10] || 'th');
    }
    if (path.indexOf('baseball/') === 0) { return ord(period); }
    if (path.indexOf('hockey/') === 0) { return period <= 3 ? ord(period) : 'OT'; }
    if (path.indexOf('football/') === 0) { return period <= 4 ? period + 'Q' : 'OT'; }
    if (path.indexOf('soccer/') === 0) { return period <= 2 ? period + 'H' : 'ET'; }
    if (path.indexOf('basketball/') === 0) {
      if (path.indexOf('mens-college-basketball') >= 0) {
        return period <= 2 ? period + 'H' : 'OT';
      }
      return period <= 4 ? period + 'Q' : 'OT';
    }
    return '';
  }

  // Behind or level: the favourite is named on the row, the score is not.
  // Finished, an upset means the favoured side lost. In progress it means the
  // game is still close enough for one -- the row carries how close counts and
  // which period must be done first, so the sport's own numbers stay in config.
  function upsetHappening(row, scores, state, period) {
    var victim = row.dataset.upset;
    if (!victim || (state !== 'in' && state !== 'post')) { return false; }
    var other = victim === 'home' ? 'away' : 'home';
    if (scores[victim] == null || scores[other] == null) { return false; }
    var mine = Number(scores[victim]), theirs = Number(scores[other]);
    if (state === 'post') {
      return mine < theirs || (mine === theirs && mine + theirs > 0);
    }
    var close = (row.dataset.close || '').split(':');
    if (close.length !== 2) { return false; }
    if (!period || period <= Number(close[1])) { return false; }
    return (mine - theirs) <= Number(close[0]);
  }

  // The row carries what would colour it -- "good:home:LD|bad:away:L" -- so
  // only the result is worked out here. Good beats bad where both apply:
  // Michigan beating Ohio State is the good one, not the quiet one.
  function moodFor(row, scores) {
    var spec = row.dataset.mood;
    if (!spec) { return ''; }
    var best = '';
    spec.split('|').forEach(function (part) {
      var bits = part.split(':');
      var side = bits[1], letters = bits[2] || '';
      var other = side === 'home' ? 'away' : 'home';
      if (scores[side] == null || scores[other] == null) { return; }
      var mine = Number(scores[side]), theirs = Number(scores[other]);
      var result = mine === theirs ? 'D' : (mine > theirs ? 'W' : 'L');
      if (letters.indexOf(result) < 0) { return; }
      if (bits[0] === 'good') { best = 'good'; } else if (!best) { best = 'bad'; }
    });
    return best;
  }

  // A rival level or losing while the game is on, whatever the ranks say.
  // "side:LD:after_period:after_clock" -- -1 for no clock rule.
  function rivalInTrouble(row, scores, state, period, clock) {
    if (state !== 'in') { return false; }
    var spec = (row.dataset.rival || '').split(':');
    if (spec.length !== 4) { return false; }
    var side = spec[0], other = side === 'home' ? 'away' : 'home';
    if (scores[side] == null || scores[other] == null) { return false; }
    var after = Number(spec[2]), limit = Number(spec[3]);
    if (after) {
      var deep = period > after;
      if (!deep && limit >= 0 && period === after) {
        deep = typeof clock === 'number' && clock <= limit;
      }
      if (!deep) { return false; }
    }
    var mine = Number(scores[side]), theirs = Number(scores[other]);
    var result = mine === theirs ? 'D' : (mine > theirs ? 'W' : 'L');
    return spec[1].indexOf(result) >= 0;
  }

  function paint(row, event) {
    var comp = (event.competitions || [])[0];
    if (!comp) { return; }
    var type = ((comp.status || {}).type) || {};
    var state = type.state || '';
    var when = row.querySelector('.when');
    if (!when) { return; }
    var scores = {};
    (comp.competitors || []).forEach(function (c) {
      scores[c.homeAway] = c.score;
    });
    // A draw has no losing side, so the word carries it.
    var drawn = state === 'post' && scores.home != null
      && String(scores.home) === String(scores.away);
    var losing = null;
    if (state === 'post' && !drawn && scores.home != null && scores.away != null) {
      losing = Number(scores.home) < Number(scores.away) ? 'home' : 'away';
    }
    // A delay reads as in-progress and buries the period in ESPN's own prose
    // ("Rain Delay, Top 1st"), so it is rewritten the way the build writes it.
    var name = String(type.name || '').toUpperCase();
    var delayed = name.indexOf('DELAY') >= 0;
    // Never played: ESPN calls these "post", which would read as Final, and
    // at 0-0 would be struck through as a draw.
    var calledOff = name.indexOf('POSTPONED') >= 0 || name.indexOf('CANCEL') >= 0
      || name.indexOf('SUSPEND') >= 0;
    var stopped = periodLabel(row.dataset.path || '', (comp.status || {}).period);
    if (calledOff) {
      applyState(row, {state: state, text: type.description || 'Postponed',
                       drawn: false, losing: null});
      return;
    }
    var st = {
      state: state,
      text: delayed ? (stopped ? 'Delay - ' + stopped : 'Delay')
        : state === 'post' ? 'Final'
        : state === 'in' ? (type.shortDetail || 'live')
        : when.textContent,
      home: scores.home, away: scores.away,
      drawn: drawn, losing: losing,
      // An upset shows while it is happening; the rest are results, so they
      // wait for the final whistle.
      mood: (upsetHappening(row, scores, state, (comp.status || {}).period)
             || rivalInTrouble(row, scores, state, (comp.status || {}).period,
                               (comp.status || {}).clock)) ? 'good'
        : (state === 'post' ? moodFor(row, scores) : '')
    };
    applyState(row, st);
    // A game still to start has nothing worth remembering: the build's own
    // time is already the right answer.
    if (state !== 'pre') { remember(row.dataset.game, st); }
  }

  function primeFromMemory() {
    try {
      var was = Number(localStorage.getItem(STAMPED) || 0);
      // Anything older than the build is the build's own line already.
      if (was) { setStamp(was, false); }
    } catch (e) {}
    var panel = todayPanel();
    if (!panel) { return; }
    Array.prototype.forEach.call(
      panel.querySelectorAll('.row[data-game]'), function (row) {
        var st = remembered[row.dataset.game];
        if (st) { applyState(row, st); }
      });
  }

  function refresh() {
    var rows = rowsToWatch();
    if (!rows.length) { return; }
    // One request per league, not per game.
    var byPath = {};
    rows.forEach(function (row) {
      (byPath[row.dataset.path] = byPath[row.dataset.path] || []).push(row);
    });
    var when = new Date();
    var stamp = when.getFullYear()
      + ('0' + (when.getMonth() + 1)).slice(-2) + ('0' + when.getDate()).slice(-2);
    Object.keys(byPath).forEach(function (path) {
      var url = 'https://site.api.espn.com/apis/site/v2/sports/' + path
        + '/scoreboard?dates=' + stamp + '&limit=400';
      fetch(url, { headers: { Accept: 'application/json' } })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (data) {
          if (!data) { return; }
          var byId = {};
          (data.events || []).forEach(function (ev) { byId[ev.id] = ev; });
          byPath[path].forEach(function (row) {
            var ev = byId[row.dataset.game];
            if (ev) { paint(row, ev); }
          });
          setStamp(Date.now(), true);
        })
        // Silence is the right failure: the page keeps the build's numbers,
        // which is exactly what it showed before any of this existed.
        .catch(function () {});
    });
  }

  // A page kept on screen across midnight shows a slate for a day that has
  // ended, and the reload that fires on returning to the app never runs
  // because you never left. So the tick watches the date as well.
  //
  // It cannot just reload until the date matches: the new build does not
  // publish until 6am, so from midnight onwards the reload would fetch the
  // same page and go round again every minute. The time of the last one
  // therefore lives in sessionStorage -- which survives a reload, where a
  // variable would not -- and holds the next off for half an hour. That also
  // picks the morning's build up shortly after it lands.
  var ROLL_MS = 30 * 60 * 1000;
  function mayReloadForNewDay() {
    if (localDay() === BUILT) { return false; }
    try {
      var last = Number(sessionStorage.getItem('rolled') || 0);
      if (Date.now() - last < ROLL_MS) { return false; }
      sessionStorage.setItem('rolled', String(Date.now()));
      return true;
    } catch (e) {
      // With no storage there is no way to hold the next reload off, and a
      // loop is far worse than a stale page: returning to the app still
      // catches the new day.
      return false;
    }
  }

  function start() {
    if (live) { clearInterval(live); }
    if (document.visibilityState !== 'visible') { return; }
    refresh();
    live = setInterval(function () {
      if (document.visibilityState !== 'visible') { return; }
      if (mayReloadForNewDay()) { location.reload(); return; }
      refresh();
    }, LIVE_MS);
  }

  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'visible') { start(); }
    else if (live) { clearInterval(live); live = null; }
  });
  primeFromMemory();
  start();
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
      // Cross-origin font responses are opaque and cache.put rejects them;
      // swallowing that keeps the fetch handler from logging on every load.
      caches.open(CACHE)
        .then(function (c) { return c.put(e.request, copy); })
        .catch(function () {});
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


def _clock(when):
    """'9:10 am' -- %-I is not portable on Windows, so strip the zero by hand."""
    return when.strftime("%I:%M %p").lstrip("0").lower()


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

    # Yesterday is kept as an extra tab -- last night's finals are the thing
    # you most want on waking -- so the run covers `days` from today, plus one
    # behind it. Today stays the tab the app opens on; it is now the second.
    tabs, panels = [], []
    for offset in range(-1, days):
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
        # Only today's panel carries the stamp: no other day has numbers that
        # can go out of date while you are looking at them.
        stamp = ('<div class="updated" id="updated">Updated %s</div>'
                 % _clock(datetime.now(tz))) if offset == 0 else ""
        panels.append(
            '<section class="day" id="%s"><h1>%s</h1>%s%s</section>'
            % (ident, day.strftime("%A, %B %d").replace(" 0", " "), stamp, body))
        print("  %s  %d games" % (day.isoformat(), len(games)))

    page = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,'
        'viewport-fit=cover">'
        '<title>Games</title>' + render.FONT_LINK +
        '<link rel="manifest" href="manifest.webmanifest">'
        '<meta name="theme-color" content="#16161a">'
        '<meta name="apple-mobile-web-app-capable" content="yes">'
        '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">'
        '<link rel="apple-touch-icon" href="icon-180.png">'
        # Without this a desktop browser asks for /favicon.ico, which the site
        # does not ship, and shows a blank tab icon after the 404.
        '<link rel="icon" href="icon-192.png">'
        '<style>%s%s</style></head><body><div class="wrap">'
        '<nav class="days" id="days">%s</nav>%s'
        '<footer>From ESPN. Times in %s.</footer>'
        '</div><script>%s</script></body></html>'
    ) % (render.CSS, APP_CSS, "".join(tabs), "".join(panels),
         config.get("timezone", "local"),
         APP_JS.replace("%%BUILT%%", today.isoformat())
                .replace("%%TZ%%", config.get("timezone", "America/New_York")))

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
    ap.add_argument("--days", type=int, default=15,
                    help="days from today; yesterday is always added as well")
    ap.add_argument("--out", default=SITE)
    args = ap.parse_args(argv)

    config = sports_daily.load_config()
    sheets.load(config)
    # The shared colour list. THIS is the build the workflow runs -- putting it
    # only in sports_daily.main() left it in a path that never executes.
    print("  " + sheets.load_colors(config))
    out, size = build(config, days=args.days, out=args.out)
    print("wrote %s (%.0f KB page)" % (out, size / 1024.0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
