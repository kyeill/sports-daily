
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
