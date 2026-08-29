
## 2026-08-29 — regional networks, yesterday tab, live-state memory

- **No regional networks anywhere.** The national-only rule was a per-league
  flag that only the NFL, NBA and MLB carried, which is why Red Wings games
  printed `FanDuel SN DET` and Pistons games (feed: `FanDuel SN DET Ext`)
  printed nothing. Now global; the flag is gone from config.json. Verified
  over seven dates and every league that it strips only regional feeds —
  SECN+, ACCN, ACCNX and the national channels are untouched, and no
  genuinely national channel is mislabelled by ESPN.
- **MLS Season Pass renders as Apple TV**, which is the actual service.
- **Yesterday is now a tab**, added in front of today rather than replacing a
  day at the end: `--days 15` builds 16 tabs. The app still opens on today,
  found by id — and so does the live-score poller, which would otherwise
  have been polling yesterday.
- **Reload no longer flashes the build's numbers.** The last live state per
  game is kept in `localStorage` under `live:<build-date>` and painted on
  load, so a reload shows what the page last knew instead of a 6am start
  time and two records. Older keys are pruned on write.

## 2026-08-29 (later) — weekday label, spread at final

- Yesterday's tab reads **"Fri"** like every other day; only today is named.
- **ESPN drops the odds node the moment a game is final** — measured over 315
  finished games across seven leagues and four dates, not one kept a spread.
  So a build never prints a line on a finished game, and the spread survives
  through the whole of live play, which is the wanted behaviour. A page left
  open through the final whistle was the exception: the live script rewrote
  the status and struck the loser but left the spread. It now removes it on
  the same pass.

## 2026-08-29 (later still) — reload on the day rolling over

A page left on screen across midnight kept showing the finished day's slate:
the reload that fires on returning to the app never ran, because you never
left. The 60-second tick now checks the date too.

It cannot simply reload until the date matches — the new build does not
publish until 6am, so from midnight the reload would fetch the same page and
go round again every minute. The time of the last reload is kept in
`sessionStorage` (it survives a reload, where a variable would not) and holds
the next off for half an hour, which also picks the morning's build up
shortly after it lands. With no storage available it does nothing at all: a
stale page is far better than a reload loop.

Verified in a browser with a stale build date and a 2-second tick: eleven
ticks produced exactly one reload, and backdating the throttle past the
window produced exactly one more.

## 2026-08-29 (later still) — "Updated" stamp, and a favicon

- **`Updated 9:10 am` under the date on today's panel only** — no other day
  has numbers that can go stale while you look at them. It is the time the
  numbers were last confirmed against ESPN, not the build time: the build
  writes its own clock into the page, every successful poll replaces it, and
  the value is stored so a reload shows the real last update instead of
  jumping back to 6am. Formatted in the page's own timezone via `Intl`, so a
  PC set to another zone still reads ET.
- Styled with the section headings' font, size and colour but **not** their
  uppercase tracking — directly under the date, that reads as a heading for
  the day rather than a note about it.
- **Added `<link rel="icon">`.** The page declared only an
  `apple-touch-icon`, so desktop browsers asked for `/favicon.ico`, took a
  404 and showed a blank tab icon. The icons were already being shipped.

## 2026-08-29 (later still) — finished games sink

A game that is over now falls to the bottom of its section, with several
finals ordered among themselves by original start time. Games still to come,
and games in progress, keep the order the build gave them.

Done in **both** places, by the same rule, so a reload changes nothing: the
build sorts on `(finished, start)`, and the live script re-sorts a card when
a row reaches `post`. For National the flag sits *after* the bucket in the
sort key — the two halves are separate cards, so a final sinks within its own
half rather than crossing the gap into the other one.

Rows carry `data-start` so the client can reproduce the build's order. The
`.row:last-child` border rule reapplies by itself when rows move.

Verified: 15 section/bucket groups across three dates sort correctly with
mixed states, and in the browser a first-row game moved to the bottom on
going final, with two finals landing in start order rather than the order
they ended.
