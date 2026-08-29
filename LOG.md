
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
