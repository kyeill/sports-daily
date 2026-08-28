# Sports Daily — to-do

Last refreshed 2026-08-28. The design itself lives in `README.md`; this file is
only what is *not done*. If something here is unclear, the "Traps" section of
the README explains why most of it is the way it is.

## Open

### Playoff odds for three sports have no usable source

The 20% qualification floor (`race_min_odds`) is real for four sports only:

* **NFL / NBA** — ESPN power index, `probmakeplayoffs`
* **MLB** — FanGraphs playoff odds
* **College football** — ESPN FPI, where `probmakeplayoffs` means the CFP

The gaps, each investigated on 2026-08-24 and each a dead end for now:

* **NHL** — MoneyPuck serves a "get a license" page and must not be scraped.
  ESPN's `/futures` carries only Stanley Cup / conference / division *winner*
  markets — implied championship odds, a different quantity, useless as a
  qualification floor.
* **College basketball** — no probability anywhere, only BPI
  `projectedtournamentseed`.
* **Soccer** — no playoff concept to have odds about.

Where no source exists the floor is skipped and the race falls back to
standings position, which is verified working. Options if this is ever picked
up: find another feed, or run a simple season simulator off the standings.
Doing nothing is a legitimate answer — the fallback is not broken.

### Two rules have never run against live data

Both are spread-based, and **ESPN only publishes odds for upcoming games** —
completed games return an empty `odds` array. So neither can be tested on a
historical date; readings taken on 2025 dates were meaningless.

* **College football blowout filter** (`max_spread: 30`, Syracuse exempt, four
  marquee Saturday windows exempt with ±60 min slack). Verified only against
  fabricated cases. **First real check: Saturday 5 September 2026.** Watch that
  the exempt windows actually match — the network and local-time matching is
  the fragile part.
* **College basketball blowout filter** (`max_spread: 15`, Syracuse exempt, no
  TV windows). Could not be verified at all: the 2026-27 season had not started
  and ESPN had no odds three months out. **First real check: November 2026.**

A game with no spread is always kept, so the failure mode is "rule silently
does nothing", not "games disappear".

## Recently closed — do not reopen

Settled on 2026-08-28.

* **Five sections** — Main Slate, Highlights, Football, Basketball, National, in
  that fixed order, replacing one section per league ordered by kickoff. The
  rules are written out in the README; the bowl test (Big Ten, ranked, or
  Power Four both sides) and the two halves of National are the parts worth
  re-reading before changing anything.
* **National broadcasts** for MLB/NBA/NHL are an inclusion rule of their own,
  roughly 4-5 games a night when all three are in season. ESPN's `national`
  flag is useless for this and must not be used.
* **College hockey** is Michigan, Cornell and the NCAA tournament. Conference
  tournaments are indistinguishable from regular season in ESPN's data.
* **Stripe colours** — three tests, each of which earned its place:
  `invisible_colour` (too dark), `washed_out` (too pale, which is what silver
  is), and the vivid exemption for bright colours whose luminance lies.
  Brightness alone was wrong twice; ask what kind of colour it is.
* **Display names** live in `team-names.json`, shared with the standings page.

Settled on 2026-08-26.

* **Crests** — `logos.py` measures both 500px variants and writes 77
  `logo_overrides` into `config.json`. Where neither variant reads, the mean
  colour of the default one decides: navy (r < g < b) and near-neutral crests
  keep the white silhouette, anything else takes the coloured variant. 22
  teams are left unreadable on purpose. **A backing disc was built and
  rejected** — only ~3% of teams would carry one, so it reads as a mistake,
  and a uniform version is impossible: ESPN's pre-composited files are 4096px
  and 150-270KB, and compositing the dark variant onto the team colour puts
  the Red Wings' red wheel on a red disc. Do not propose it again.
* **Row layout** — two stacked team lines on a shared four-column grid. See
  "How a row is built" in the README.
* **Shortening names on phones** — by measured width, not character count, and
  using ESPN's short name rather than its abbreviation. Both alternatives were
  tried and are recorded in the README; neither is worth revisiting.

These sat in this file as open questions and were all settled on 2026-08-24.

* **College tier 2** — settled in full. CFB: any Big Ten game, any AP top-25
  team, Power Four midweek only, FOX/CBS/NBC/ABC Saturdays only (FBS feed
  only), all bowls and CFP. CBB: Big Ten, ranked, FOX/CBS/NBC/ABC Fri-Sun.
* **College basketball postseason** — settled via `postseason_rules`, which
  *replace* the regular rules rather than OR-ing with them (every tournament
  team is ranked and on a major network, so OR-ing would admit the whole
  bracket). `include_postseason` stays off for basketball on purpose; it is not
  an oversight.
* **Soccer** — all 14 competitions configured. "The race" turned out not to
  need defining for a league table: tier 3 is rule-driven instead
  (Arsenal/Chelsea always, the big three Sat-Sun, table top five Sat-Sun
  Jan-May, FA/Carabao semis and finals).
* **Games Back tracking** — shipped. `race.snapshot()` builds the daily row,
  `record_history()` writes `output/history/<league>.csv`, and derived rows
  carry the gap inline ("Lions 2 GB", "Red Wings 6 pts back" — hockey uses
  points, chosen from the league's sport, not from whether a `points` field
  happens to exist). History is written only when the run is for today.
