# Sports Daily — the day's games, filtered

Builds a single self-contained HTML page listing the day's games across NFL,
NBA, MLB, NHL and the Premier League, with **my teams** pinned at the top and everything
else grouped by sport. Data comes from ESPN's
public scoreboard API — no key, no account, no scraping.

Everything you would change day to day lives in **`config.json`** in this
folder. A Google Sheet front end exists and is optional; it is off.

```
python site.py                     # builds the 8-day app into output/site/
python sports_daily.py                    # writes output/today.html
python sports_daily.py --text             # print to the console instead
python sports_daily.py --date tomorrow    # or 2026-09-05, 09/05, yesterday
python sports_daily.py --check            # validate the sheet's team names
python sports_daily.py --no-sheet         # ignore the sheet, use config.json only
python sports_daily.py --open             # open the page when done
```

Python is not on PATH. Use the full interpreter path:
`C:\Users\kyleh\AppData\Local\Programs\Python\Python312-arm64\python.exe`

## The app

**Live at https://kyeill.github.io/sports-daily/** — open it on a phone and
Share -> Add to Home Screen for an icon and a full-screen launch.

`site.py` builds an installable web app into `output/site/`: fifteen days in
one page with a sticky day picker, plus a manifest, icons and a service worker.
Every day is inlined, so switching days is instant and works offline — no fetch,
no JSON round trip, ~62KB for the lot. A cold build takes about two minutes.

The page is **dark only**, deliberately: it is read at a glance and should look
the same on every device rather than following each one's system setting.

GitHub Actions rebuilds and publishes it to GitHub Pages twice a day
(`.github/workflows/build.yml`), which is what makes it work when this machine
is off. On a phone, open the Pages URL and **Add to Home Screen** for an icon
and a full-screen launch.

Verified from a bare clone: the build needs nothing but Python and `requests`.
Verified live: the service worker registers and caches the page and the ESPN
logos, so a loaded day survives going offline.

**Nothing depends on a machine at home.** The cloud build also records the
games-back history and commits it back to the repo, so it accrues every day
whether or not anything local ever runs.

`sports_daily.py` still works locally for a single day or an arbitrary date --
useful for checking a rule change before pushing -- but it is optional.

## Editing your teams

Three lists at the top of `config.json`, keyed by league:

| key | meaning |
| --- | --- |
| `favorites` | pinned at the top, and drives that league's playoff race |
| `following` | pinned, but never drives a race (the Cavaliers case) |
| `watchlist` | Other highlights; the `note` becomes the badge on the row |

A `watchlist` entry is `{"team": ..., "note": ..., "expires": ...}` where
`expires` is optional `YYYY-MM-DD` and drops the row once the date passes.

After any edit:

```
python sports_daily.py --check
```

which validates every name against ESPN and flags typos, names that resolve
nowhere, and ambiguous entries — `Michigan` matches eight teams in college
football, including Michigan State, who is a rival rather than a favorite.

A broken edit reports the offending line rather than a traceback. Notepad is
fine: it writes a BOM, and the loader reads `utf-8-sig` for exactly that reason.

The nested `rules`, `tier3_rules` and `postseason_rules` blocks are where the
soccer and March Madness logic lives; a subtle change there alters behaviour
without breaking anything visibly.

## The optional control sheet

Off by default, and not needed. `sports-daily-control.xlsx` (regenerate with
`make_template.py`) is a template you can import into Google Sheets, share as
**"anyone with the link can view"**, and point `control_sheet.sheet_id` at. Its
only advantage is editing from a phone. When set, its two tabs override the
three team lists and the per-league options above.

It is read over the gviz CSV endpoint, which needs no credentials.
Deliberately not gspread — that pulls in `cryptography`, which is what broke on
this win-arm64 box during the dynasty rebuild.

**Teams tab** — `Sport | Team | Tier | Note | Expires`

| column | meaning |
| --- | --- |
| Sport | NFL, NBA, MLB, NHL, EPL, CFB, CBB, CHKY |
| Team | full name; validated against ESPN by `--check` |
| Tier | `favorite` (pinned, drives the race), `follow` (pinned only), or `watch` (Other highlights) |
| Note | shown as the badge explaining why a highlighted team is there |
| Expires | optional `YYYY-MM-DD`; a past date drops the row automatically |

`Expires` is what keeps a manual row from silently outliving its reason. Most
of the time there is nothing to expire: Key opponents is derived from live
standings, not typed in.

**Options tab** — `Scope | Option | Value | Notes`. Scope is `All` or one sport.

| option | effect |
| --- | --- |
| `enabled` | turn a whole league off |
| `show_all_games` | show that league's entire slate |
| `national_tv_only` | keep only national broadcasts |
| `standalone_only` | keep games that are the only one in their kickoff slot |
| `include_postseason` | every playoff game, whatever else is set |
| `playoff_race` | add live race opponents to Key opponents (see below) |
| `race_from_month` | month the race logic starts, e.g. `11` |
| `race_min_odds` | playoff-odds floor as a percent, e.g. `20` |
| `conferences` | either team's conference matches (substring) |
| `power_conferences` + `power_conference_days` | conference list, limited to given days |
| `major_networks` + `major_network_days` | network list, limited to given days |
| `note_matches` | headline contains one of these words |
| `rules` | composite tier-2 rules: every condition in one rule must hold |
| `tier3_rules` | the same shape, but the game lands in Key opponents |
| rule `round` | matches `event.season.slug` (`league-phase`, `round-of-16`, `mls-cup`) |
| rule `clubs_from` | at least one side belongs to that competition |
| rule `table_top` | at least one side is this high in the league table |
| rule `days` / `months` | limit a rule to certain weekdays or months |
| rule `source` | which feed the game came from, e.g. `FBS` |
| `exclude_exhibitions` | global: drop preseason and friendlies (default on) |
| `postseason_rules` | per-round rules that replace the regular ones in a tournament |
| rule `require` | the rule applies only when the headline contains this |
| `race_until_season_end` | end the window at the real end of the regular season |
| `race_last_days` | alternative: run only this many days before it ends |
| `race_only_last_spot` | just the last-spot holder, skipping the division leader |
| `race_until_settled` | stop once your team clinches or is eliminated |
| `hide_finished` | drop games already over |
| `show_odds` | the spread |
| `show_records` | W-L beside team names |
| `timezone` | IANA name, `All` scope only |

Favorites and watchlist teams are **always** kept regardless of the options —
the rules only ever add games, never subtract. The **one exception** is
`exclude_exhibitions` (on by default): preseason games and friendlies are
dropped everywhere, even for a favorite, because nothing is at stake. A blank cell means "leave it
alone", never "turn it off".

Edits land on the next run; the sheet is re-read every two hours (and always on
a manual run). If it is unreachable the last working copy is used and the page
says so at the top, rather than quietly rendering an empty watchlist.

After editing team names, check them:

```
python sports_daily.py --check
```

```
  ok   MLB              favorite  Philadelphia Phillies
  BAD  MLB              watch     Phillhies -- did you mean Philadelphia Phillies?
```

## How each sport is set up

**NFL** — Lions pinned; for neutral games, `standalone_only` keeps exactly the
standalone windows and nothing else, plus every postseason game.

Preseason is excluded globally, which matters here: the standalone rule cannot
tell August from November on its own, and a preseason week has five nationally
televised games alone in their slots.

`standalone_only` is a time-slot rule, not a network list: a game qualifies when
it is the only one kicking off at its time. Verified against real weeks, that
catches TNF, SNF, MNF, all three Thanksgiving games and the December Saturday
specials, and rejects all eleven regional Sunday-window games. It needs no
maintenance when broadcast deals change, and `national_tv_only` would not work
here at all — ESPN marks the regional CBS and FOX windows as national, so on a
typical Sunday 13 of 13 games qualify.

A December Sunday comes out at 2 games kept from 14.

**MLB** — Tigers pinned, plus the AL Central and wild card races from July.
**No tier 2 at all**: a neutral baseball game does not earn a row. On a typical
night that is one or two games, not fifteen.

**NBA** — Pistons pinned, Cavaliers **followed** (their games appear, but they
never drive the race). No tier 2. Race runs **March 1 to the end of the regular
season**, shows only the team holding the last playoff spot (seed 10, the last
play-in place), and stops the moment the Pistons clinch or are eliminated.

**Postseason** — every playoff game in all four American leagues, from the
wild card round to the final. All-star games are *not* postseason in ESPN's
data (they are season type 2 with teams like "AL VS NL"), so they stay out
without needing a rule.

**NHL** — Red Wings pinned, same race rules. No tier 2, no odds gate (no source
exists for hockey), so `race_until_settled` and the short window do the work
that the odds floor does elsewhere.

`favorite` versus `follow` matters when a league has two: the race follows your
favorites **in the order listed**, so it cannot drift to the other team just
because they climbed the standings.

**College football / basketball / hockey** — Michigan and Cornell pinned in all
three. Ohio State, Michigan State and Notre Dame are watchlist rivals in football
and basketball, tagged `Rival`; Syracuse rides along in the same two, tagged
`Other`. Every CFP and college hockey postseason game is included;
March Madness has **its own rules, which replace the regular-season ones**:

* **First weekend** (First Four, 1st and 2nd rounds) — Big Ten teams, Notre Dame
  and Syracuse
* **Sweet 16 onward** — every game, ignoring rankings and networks
* **NIT and the College Basketball Crown** — the same short list throughout:
  Big Ten, Notre Dame, Syracuse (favorites always come through anyway)

That replacement is the point. In March every tournament team is ranked and on a
major network, so leaving the normal rules switched on would pull in the whole
bracket from day one.

Rules are tried in order, and a rule's `require` failing means "not this rule"
rather than "not eligible" — so an NIT game headlined "NIT - 1st Round" falls
past the NCAA rules, which require the championship headline, to the one meant
for it. Getting that wrong would have silently swallowed the NIT.

| date | round | kept |
| --- | --- | --- |
| Mar 17 | First Four (+ NIT) | 0 of 10 |
| Mar 20 | 1st Round | 3 of 16 |
| Mar 22 | 2nd Round | 3 of 14 |
| Mar 26 | Sweet 16 | 4 of 4 |
| Mar 28 | Elite 8 | 2 of 2 |
| Apr 4 | Final Four (+ Crown semis) | 2 of 4 |
| Apr 6 | National Championship | 1 of 1 |
| Mar 19 | 1st Round | 6 of 16 |
| Apr 1-2 | Crown | 2 of 34 NIT/Crown games — Minnesota and Rutgers |

One display quirk: during the tournament ESPN's curated rank **is the seed**, so
a row reads "#9 Iowa at #8 Clemson" rather than showing AP ranks.

**College football tier 2:** any **Big Ten** game; any game with an **AP top-25**
team (ESPN's curated rank switches to the CFP rankings once they exist, which is
what you want); any **Power Four vs Power Four** game **midweek only**; any **FOX/CBS/NBC/ABC**
game **on Saturdays involving an FBS team**; and every bowl and CFP game.

The FBS requirement is why the two college-football feeds are labelled: FBS is
`groups=80`, FCS is `groups=81`, and a rule can demand the game came from the
FBS one. Without it an FCS season opener on ABC qualifies as a "National Game".

**College basketball tier 2:** any Big Ten game, any ranked team, and
FOX/CBS/NBC/ABC games **Friday through Sunday**.

**College hockey tier 2:** none — Michigan and Cornell, conference tournaments
and the NCAA tournament.

Measured against real days last season:

| day | kept |
| --- | --- |
| Sat Oct 18 (CFB) | 24 of 102 |
| Fri Oct 24 (CFB) | 1 of 5 — the one midweek Power Four game |
| Sat Dec 27 (bowls) | 8 of 8 |
| Sat Jan 24 (CBB) | 24 of 136 |
| Tue Feb 3 (CBB) | 9 of 31 |
| Fri Mar 20 (hockey) | 5 of 5 — conference tournaments |
| Sat Mar 28 (hockey) | 2 of 2 — NCAA regionals |

Two things make college different from the pro leagues:

* **Full names are mandatory.** Matching is substring, so `Michigan` also means
  Michigan State, Central Michigan and six more — and Michigan State is supposed
  to be a rival, not a favorite. `--check` now flags any entry matching more
  than one team.
* **College football needs two fetches.** FBS is `groups=80` and FCS is
  `groups=81`; Cornell is Ivy League, so an FBS-only call cannot see them.
  `params_variants` fetches both and dedupes by event id.

**Soccer** covers fourteen competitions, because following a club means
following it everywhere. A team is listed **once** under `EPL`, `MLS` or
`USMNT` and inherits into every competition in its group via `team_group`.

*Tottenham* — every match, in the league, both domestic cups and all three
European competitions. Tier 2: any **midweek** Premier League match; any
**Champions League knockout**; any **league-phase** tie with an English club;
Europa and Conference **knockouts** involving an English club. Tier 3: **Arsenal
and Chelsea** in any competition; **Man City, Man United, Liverpool** on
Saturdays and Sundays; anyone in the **top five of the table** on a weekend from
January to May; and **FA/Carabao Cup semi-finals and finals**.

*Atlanta United* — every match including the U.S. Open Cup, Leagues Cup and
Concacaf Champions Cup. Tier 2: **MLS playoffs**, and **Leagues Cup knockouts**
involving at least one MLS club. No rivals.

*USMNT* — competitive matches only. Friendlies are excluded by simply not
fetching `fifa.friendly`; qualifying, the Gold Cup, Nations League and the World
Cup are each their own competition.

Measured on real match days: Wed Dec 3 midweek round 6 of 6; Sat Jan 17 5 of 7;
UCL league phase Jan 28 6 of 18; UCL knockouts Mar 10 4 of 4; MLS playoffs Nov 1
5 of 5; Leagues Cup quarter-finals 4 of 4.

## Tags

Deliberately narrow. A row carries at most two, and only when they say
something the row does not:

* **`Division Chase`, `Wild Card Chase`, `Playoff Spot Chase`** — the
  standings-derived teams, alongside the gap ("2 GB", "6 pts back")
The **round** is not a tag. It goes on a single line under the matchup, along
with everything else about the state of the tie:

```
World Series Gm 3 (LAD 2-1)
Stanley Cup Final Gm 4 (Tied 2-2)
Carabao Cup Second Round
Champions League R16 - 2nd Leg (3-1 ARS)
Pop-Tarts Bowl
```

For a club that plays across several competitions the competition leads the
line, unless the round already names it -- "MLS Cup", not "MLS MLS Cup".
Playoff rounds are spelled out -- First Round, Sweet Sixteen, AL Championship
Series -- through `round_spellings`. European rounds abbreviate to R16 and R32, and the aggregate comes from ESPN's
own `series.competitors` figures rather than the prose headline.

A named round suppresses the venue: a bowl game does not also need its stadium.
Neutral-site games with no round still show where they are played.

ESPN writes the series as "LAD lead series 2-1" or "Series tied 1-1"; both are
shortened to fit alongside the round.

Underneath the matchup, a detail line carries the state of a tie: the game
number and series score for American playoffs ("Game 3 · LAD lead series 2-1"),
the aggregate for two-legged European ties ("Arsenal advance 3-1 on aggregate"),
and the gap for a standings-derived team ("2 GB").

Everything else was removed: `Ranked`, `Big Ten`, `Power Four`, `National
Game`, `Standalone`, `Midweek`, `Knockout`, `Rival` and the rest merely
restated the section they were sitting in.

Round names come from two different places. The American leagues put them in
the note headline (`World Series - Game 1`, trimmed to `World Series`); soccer
puts them in `season.slug`. The slug check is a **whitelist** of knockout words,
because league slugs are unpredictable — the Premier League calls its regular
season `2025-26-english-premier-league`, which a blacklist turned into a tag.

## What sits next to a team name

`team_detail` per league: `record` for the NFL and all three college sports,
`division_place` for MLB, the NBA and the NHL ("2nd"), `table_place` for the
Premier League and MLS ("3rd"), and `none` for every other soccer competition,
where a cup has no table to place anyone in.

Places come from the **current** standings, so a team that has since been
relegated has no place at all when you browse an old date.

## The colour stripe

The stripe down the left of each row is:

1. **your team's colour** when you are involved
2. against a **rival** (a watchlist entry noted `Rival`), the **opponent's**
   colour -- you are watching for the rival to lose
3. otherwise the colour of whichever team makes the game interesting
   (Syracuse, Arsenal, the last-spot holder)
4. **black** when both sides are rivals

When none of that applies, two rooting rules decide (`tint_rules`), conference
first: back the **Big Ten** side against an outsider -- never Ohio State or
Michigan State -- and only when both or neither are Big Ten does the
**unranked** side win. So a ranked Big Ten team against an unranked outsider
takes the Big Ten colour, while two Big Ten teams fall through to the underdog.
Failing all of it, the home team.

`team_names` does the same for names ESPN writes differently from how people
say them -- Tottenham comes back as "Spurs".

`team_colors` in `config.json` overrides ESPN where its idea of a team's colour
is not the one people picture -- Syracuse comes back navy rather than orange,
and Michigan blue rather than maize.

## Networks

ESPN labels every broadcast as **national**, **home** or **away**, so the NFL,
NBA and MLB show the national feed only (`national_only_display`). A game
carried solely on regional networks shows no network at all, which is the
honest answer — the regional feed is only useful if you happen to get it.

**Streaming is listed only when it is the only way to watch.** Anything in
`streaming_networks` -- Peacock, Paramount+, ESPN+, Apple TV and the rest -- is
dropped when the game is also on real television, and kept when it is not. So
a Premier League match on USA and Peacock shows USA; an MLS game on Apple TV
shows Apple TV.

Only **one** network is listed -- the March Madness TBS/truTV simulcast does
not need both. MLB.TV is flagged *national* despite being a streaming service,
so `hide_networks` still does real work, as does hiding `Universo` and `TUDN`.

## Section order

Your teams first, then one section per sport **ordered by when that sport's
first game starts**, so a 7:30am Premier League match leads and a 10pm West
Coast game trails. Ties are broken by `sort_rank` in `config.json`: college
football, college basketball, the Premier League, other soccer, NFL, MLB, NBA,
NHL, college hockey.

**Rivals** sit in their own block directly under My Teams: Ohio State,
Michigan State, Notre Dame, Arsenal and Chelsea. A rival playing one of your
teams is already in My Teams and is not repeated.

In **My Teams** the league is not named, since the team implies it -- except in
soccer, where Tottenham and Atlanta United appear across half a dozen
competitions and the badge is the only way to tell the Carabao Cup from the
league.

College football and basketball each split into **Ranked** and **Other**
(`split_ranked`), since a top-25 game is a different proposition from the rest
of the slate.

Highlighted teams sit in their own sport rather than a separate block — the tag
on the row already says why the game is there.

## The playoff race (derived highlights)

With `playoff_race` on, up to two teams are added to Other highlights each day
from live standings, so tier 3 maintains itself:

* **your division's leader** — or, when you lead it, your nearest chaser
* **whoever holds the last playoff spot** — or, when that is you, the first team
  on the outside

Both sides of one game can qualify: when the division leader plays the wild card
holder, the row carries both tags.

### The odds floor

`race_min_odds` keeps a dead season quiet. ESPN's elimination flag is
mathematical and arrives far too late — a team can be alive on paper and
finished in practice for weeks — so the race also checks a playoff-odds floor:

| league | source | field |
| --- | --- | --- |
| NFL | ESPN FPI | `probmakeplayoffs` (0-100) |
| NBA | ESPN BPI | `probmakeplayoffs` (0-100) |
| College football | ESPN FPI | `probmakeplayoffs` — CFP odds |
| MLB | FanGraphs | `endData.poffTitle` (0-1, scaled) |
| NHL | none | floor ignored, standings position used |
| College basketball | none directly | BPI has `projectedtournamentseed`, a seed not a probability |
| Soccer | n/a | no playoff concept; would need a top-four or title model |

**Why the NHL has nothing.** ESPN's futures endpoint does carry NHL markets
(`.../seasons/<year>/futures`) but only Stanley Cup, conference and division
winners — implied *championship* odds, a different quantity from qualifying.
Nobody is 20% to win the Cup, so feeding those into a playoff-odds floor would
silence every race. Verified, not assumed.

MoneyPuck is the obvious NHL source and **explicitly asks not to be scraped**,
so it is not used. Odds are cached for 12 hours — they move once a day at most,
and FanGraphs is somebody else's bandwidth.

The page reports the odds only while a race is live, in one quiet line: **"Detroit Lions 68% to
make the playoffs"** when the race is live, or **"MLB race hidden - Detroit
Tigers at 5% to make the playoffs (floor 20%)"** when it is not — so a blank Key
opponents section never reads as a breakage. Leagues without a source say
nothing at all rather than implying a number they do not have.

`race_until_season_end` ends the window at the **real end of the regular
season**, read from ESPN (NBA 2027-04-12, NHL 2027-04-18) rather than guessed at
a month boundary. Paired with `race_from_month: 3` that gives March 1 through
the last day of the season.

The start is anchored to **March of the year that season ends**, not simply
"month >= 3". Testing the month alone would switch the race back on in October,
when the next season starts and its April end date is still in the future.

`race_only_last_spot` drops the division-leader pick, and `race_until_settled`
ends the race on any clinch marker — clinched or eliminated, the question is
answered either way. Verified across five scenarios per league: mid-season,
final month still fighting, clinched, eliminated, and after the season ends.

`race_from_month` / `race_until_month` bound the window — NFL 11→2, MLB 7→10.
The football window **wraps the year end** and the baseball one does not, so the
check tests for a wrap rather than assuming one. Assuming a wrap made the
non-wrapping window always true, which would have left the baseball race running
in March.

It switches off before `race_from_month` (a September race is meaningless — everyone is
one game out of everything) and once ESPN marks your team eliminated. Worked
through the real final 2025 NFC standings, with the Lions moved around the
bracket:

| Lions at | Key opponents shows |
| --- | --- |
| leading the NFC North | Packers (chasing you in the NFC North) |
| a wild card spot | Bears (NFC North leader) + Packers (last playoff spot) |
| the last spot | Bears (NFC North leader) + Vikings (first team out) |
| just outside | Bears (NFC North leader) + Packers (last playoff spot) |
| eliminated | nothing |

Each of those rows carries the gap as context — "Lions 2 GB", "Red Wings 6 pts
back" — so a highlighted team says not just *why* it is there but *how close* it
is. Hockey is measured in points rather than games back, chosen from the
league's sport rather than from whether a `points` field happens to exist.

### Games back history

Every run on the current day appends one row per favorite to
`output/history/<league>.csv`: seed, record, whether you lead the division, the
gap to the division leader and the gap to the last playoff spot. One row per
team per day, so re-running is harmless, and **only ever for today** — browsing
to another date must not stamp it with standings that are current rather than
historical.

It records regardless of the race window or the odds floor, because a history
whose whole value is the shape of a season cannot be backfilled later.

**Standings are always current.** Running `--date` for a past day still uses
today's standings, so a backdated run shows a race that reflects now, not then.

## Files

| file | role |
| --- | --- |
| `sports_daily.py` | CLI entry: date parsing, collection, text output, `--check` |
| `sheets.py` | the control sheet: fetch, parse, merge, cache, fallback |
| `espn.py` | fetch + disk cache + normalize one league-day into game dicts |
| `filters.py` | tier assignment, keep/drop rules, network display |
| `race.py` | derives the playoff-race half of the watchlist from standings |
| `render.py` | the HTML page (light/dark aware, no external assets) |
| `config.json` | sheet id, league list, network names — rarely touched |
| `make_template.py` | regenerates `sports-daily-control.xlsx` |
| `run-daily.cmd` | what the scheduled task runs; appends to `run.log` |
| `register-task.ps1` | one-time task registration (needs an elevated shell) |
| `cache/` | raw ESPN JSON (30 min), sheet CSVs, team lists (a week) |
| `output/today.html` | the deliverable |

## Traps — each one cost a debugging pass

- **Do not set a browser-style `User-Agent`.** ESPN returns **403** for
  `Mozilla/5.0 ...` from a non-browser client, but serves the `requests`
  default fine. `espn.py` sends only `Accept: application/json`.
- **`ESPN+` is flagged `market: "national"`.** Trusting ESPN's own national
  flag kept 115 of 132 college basketball games on a test day. The
  `national_tv` rule matches an explicit network list instead — and the match
  keeps the `+`, because flattening `ESPN+` to `espn` collapses it onto the
  ESPN entry and reopens the same hole.
- **A private Google Sheet answers 200 with a sign-in page**, not an error.
  `sheets.py` sniffs for HTML and treats it as a failure.
- **An unreachable sheet must not read as an empty sheet** — an empty watchlist
  looks exactly like a working one with nothing in it. Last-good copy wins, and
  the page carries a banner.
- **ESPN buckets by UTC date**, so a 10pm ET game shows up under the next day.
  `collect()` re-filters on the local date, which is why a request for one day
  can legitimately show fewer games than ESPN returned.
- **`odds` can contain nulls** (seen on college football), not just be empty.
- **Baseball lists MLB.TV plus both regional feeds** on every game. Networks
  are sorted national-first, `hide_networks` entries dropped, capped at two.
- **Soccer has no 1/2/3 season type.** The phase lives in `event.season.slug`
  (`league-phase`, `knockout-round-playoffs`, `round-of-16`, `mls-cup`), which is
  what the `round` condition matches.
- **Round patterns are exact, with explicit wildcards** — `fnmatch`, not
  substring. `final` as a substring also matches `quarterfinals` and
  `semifinals`, which would silently turn "semis and finals only" into the whole
  knockout stage.
- **A cup's `/teams` list holds only this season's entrants**, so Tottenham is
  absent from the Europa League roster while playing in the Champions League.
  `--check` is group-aware and only calls a name wrong if it resolves nowhere in
  its group.
- **The scoreboard never says what country a club is from.** "Is either side
  English?" is answered by membership of `eng.1`, and "is either side an MLS
  club?" by `usa.1`, both cached for a week.
- **College hockey conference tournaments are season type 2**, not 3 — only the
  note headline ("ECAC - Semifinal") distinguishes them, and plain regular-season
  games have no headline at all. The NCAA regionals and Frozen Four *are* type 3.
- **Bowls are season type 3** with the bowl name in the headline, so
  `include_postseason` covers bowls and the CFP together.
- **`clincher` is absent until late in a season**, so a missing value must read
  as "not eliminated" rather than the reverse.
- **Playoff games are `season.type == 3`** (`slug: post-season`), with the round
  name in `notes[0].headline` -- do not try to infer them from the date.
- **Team-name matching is substring** (so `Michigan` catches `Michigan
  Wolverines`), which means short entries over-match. `--check` is the guard.
- **Config is read `utf-8-sig`** — Notepad and PowerShell write a BOM that
  plain `json.loads` rejects. (Same as dynasty.)
- **"at" / "vs" sit inside an `<a>`**, so they are inline-level boxes that
  align on their baselines. An inline-flex side holding a 20px logo has a very
  different baseline from 12px text, which dropped the word below the names;
  `vertical-align: middle` aligns them on their centres instead.
- **Team crests need the dark variant.** ESPN's default logo is drawn for a
  light background: measured on canvas, the Tottenham badge averages luminance
  35 and Ohio State's 52, both invisible on a #16161a page. Swapping `/500/`
  for `/500-dark/` gives 255 and 165. Every league tested returns 200 for the
  variant, and an `onerror` swap covers any team that does not.
- **Neutral-site games read "vs", never "at"** — `neutralSite` in the payload.
- **Soccer is written home side first** ("Fulham vs Chelsea"); every other
  sport is away at home. ESPN's `homeAway` field is the source either way.
- **`%-I` is not portable on Windows**; times strip the leading zero by hand.

Two more leagues' worth of plumbing is still in the code (`ranked_within`,
`conferences`) from the college version. Harmless, and there if college ever
comes back — add a league entry with a `path` and those rules work again.

A league can reword its own rounds with `round_overrides`: MLS turns
`eastern-conference-playoffs---round-one` into "MLS Playoffs Round One" and
`mls-cup` into "MLS Cup Final".

## Choosing a colour or a font

```
python styles.py     -> output/style-options.html
```

The same real rows rendered once per detail-line colour and once per font, so
the choice is made by looking. It also writes `output/font-options.html` with
seven Google Fonts, which are fetched over the network on first load and then
cached by the service worker.

The detail line uses the same muted grey as the kickoff times, so the matchup
leads and the context recedes.

## Reviewing every competition at once

```
python showcase.py     -> output/showcase.html
```

No real date contains an FA Cup final, a World Series game, the Frozen Four and
a Sweet 16 tie, so `showcase.py` pulls a genuine example of each from its own
date and lays all 36 onto one page: rounds, series scores, aggregates, tints,
tags and networks, exactly as they render on the day. It is the fastest way to
check a display change against every scenario at once.

## Automation

GitHub Actions runs `site.py` **once a day at 6am Eastern**, publishes the app
to GitHub Pages, and commits any new `output/history/` row back to the repo.

GitHub cron is UTC only, so two schedules fire (10:00 and 11:00 UTC) and a gate
job lets exactly one through by checking the Eastern hour. That keeps it at 6am
year-round instead of drifting an hour with daylight saving.

Both UTC slots fire, and a gate job lets exactly one through: 6am Eastern
normally, with the 7am slot acting as a **catch-up** when GitHub delays the
earlier run past the hour. It knows whether the day already built from
`output/history/_last_build.txt`, which the build itself commits.

If a league or the odds feed cannot be reached, the page says so in a quiet
line at the top of today rather than looking like a quiet day.

The history commit carries **`[skip ci]`**: without it, the push retriggers the
workflow, which commits again, forever.

Trigger a build by hand from the Actions tab, or by pushing anything.

## Environment

Python 3.12.10 win-arm64, stdlib + `requests` + `openpyxl` (template only).
**No pandas or numpy** — Smart App Control blocks numpy's ARM64 binaries on
this machine and that is not worth relitigating; see the dynasty README.
