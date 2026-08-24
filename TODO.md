# Sports Daily — to-do

## ~~Games Back tracking~~ — DONE 2026-08-24

Store games back for the four pro teams (Lions, Pistons, Tigers, Red Wings)
whenever they are **out of a playoff spot or out of the division lead**, so the
number can be shown on the page and, more usefully, tracked over time.

The raw value already arrives and is already parsed — `espn.standings()` returns
`games_behind` per team, and the division/conference seeding needed to say
*which* deficit matters is in the same rows. So the display half is small. The
"store" half is the real feature: a dated CSV per team, appended once a day, the
way `dynasty/output/history/` works — that history cannot be reconstructed
later, so the sooner it starts the more it is worth.

Sketch:

* `output/history/games_back/<league>.csv` — `date,team,games_back_division,games_back_spot,seed`
* appended by the daily run, one row per favorite per league
* skip when the team leads its division and holds a spot (nothing to record)
* show on the page next to the odds line: "Lions 68% to make the playoffs · 2 GB
  in the NFC North"

**Built.** `race.snapshot()` produces the daily row, `record_history()` writes
`output/history/<league>.csv`, and derived Other-highlights rows carry the gap
as inline context. Hockey reports points rather than games back.

## Open questions

* **College tier 2** — he has "a lot of thoughts" and will come back to it. Until
  then college shows favorites and the rivals watchlist only.
* **College basketball postseason** — CFP shows all and college hockey shows all,
  but he was undecided on March Madness; currently `include_postseason` is off
  for basketball.
* **Soccer** — deliberately last. Needs a decision on what "the race" even means
  for a league table (top four, title, relegation) before the tier-3 machinery
  can apply.
* **Playoff odds for the gaps** — NHL, college basketball and soccer have no
  usable source. Options are the standings fallback (current) or a simulator.
