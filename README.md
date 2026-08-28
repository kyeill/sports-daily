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
what you want); any **Power Four vs Power Four** game **midweek only** -- plus **week 0**, the last Saturday of August (`power_conference_extra_dates`, 08-23..08-29), where there is so little on that an unranked Power Four pairing is worth having; any **FOX/CBS/NBC/ABC**
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

`team_detail` per league: `record` for the three college sports,
`conference_place` for the NFL, MLB, NBA and NHL -- place within the conference
or league **by record** -- `table_place`
for the Premier League and MLS ("3rd"), and `none` for every other soccer
competition, where a cup has no table to place anyone in.

**In the postseason a seed is printed instead** ("2 seed"), since a
regular-season standing means nothing once the bracket starts.

Place and seed are genuinely different numbers and are computed separately.
The NFL seeds division winners 1-4 regardless of record: in 2025 Pittsburgh
held the 4 seed at 10-7 while sitting 7th in the AFC by record. Hockey orders
by points rather than win percentage, and equal records fall back to ESPN's own
seed, which already encodes the league's tiebreakers.

Places come from the **current** standings, so a team that has since been
relegated has no place at all when you browse an old date.

## The colour stripe

**White is a last resort, never a preference.** A team with any colour at all
shows it: a white stripe says nothing about who is playing, and a page of them
says less. So the order is a colour that shows, then any colour, then a washed
-out one because there is nothing else. Exactly one team ends up white --
Tottenham, and only because that is chosen.

**Silver counts as white.** The Yankees' #c4ced4 and the Cowboys' #b0b7bc read
as white on this page whatever the swatch calls them, so `washed_out()` rejects
anything light with no colour left in it. Saturation is what separates those
from a pale but real colour: Leeds' #ffcd00 is brighter than the Yankees'
silver and obviously yellow.

The cost is accepted deliberately. Stripes for the Nets, the White Sox, the
Raiders, the Spurs, the Yankees and the Cowboys now read as near-black. Their
own colour, dim, beats a stripe that could belong to anyone.

**A stripe that would read as black is otherwise swapped for the alternate.** The
Steelers become gold, the Raiders silver, the Broncos orange, the Seahawks
green -- 254 teams in all, against 615 whose primary is kept.

The test is not brightness, and it took two passes to get right. Indiana's
crimson and Michigan State's green sit at the same luminance as a navy that
vanishes, so a colour is only rejected when it is **near-neutral** (channel
spread under 40) or a **genuine navy** (r < g < b). And a **vivid** colour is
always kept, whatever its luminance: blue contributes almost nothing to that
figure, so Brighton's #0606fa scores 24 -- darker than a navy -- while being a
bright blue anyone can see. What separates them is the strongest channel, 64
for a navy against 250 for that blue, so anything peaking at 140 or above is
left alone. That exemption puts 53 teams back on their own colour, the royal
blues: the Bills, the Rams, Florida, Kentucky, Inter and four Premier League
clubs. A purple of the same darkness runs g < r < b and reads perfectly
well, which is why the Jazz keep theirs. An explicit `team_colors` override
still wins outright -- Tottenham stays navy because that was chosen.

**College hockey borrows its colours from basketball** (`colour_from`). ESPN
publishes no colour at all for any of the 115 hockey teams, so a stripe there
was simply blank. The same universities have one in basketball, which covers
16 of the 18-team NCAA tournament field; Minnesota Duluth and Bentley are the
two that stay blank.


The stripe down the left of each row is:

1. **your team's colour** when you are involved
2. against a **rival** (a watchlist entry noted `Rival`), the **opponent's**
   colour -- you are watching for the rival to lose
3. in English football, the colour of the club you are watching for --
   Liverpool and the two Manchester clubs at home and abroad
   (`tint_prefer_teams`), and any English club in Europe
   (`tint_prefer_clubs_from`). Two of them in one game has no answer, so it
   falls to the home side; the domestic cups name nobody, since both clubs are
   English by definition
4. otherwise the colour of whichever team makes the game interesting
   (Syracuse, the last-spot holder), or the home side when two qualify
5. **black** when both sides are rivals

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

## How a row is built

Two team lines stacked, sharing a four-column grid -- crest, rank, name,
record -- with the time and networks in a column of their own behind a rule.
Both teams use the same grid, so names start at the same place whether or not
a team is ranked, and records finish at the same place whatever the names do.
A competition line ("Carabao Cup Second Round") is a third row of that grid
rather than an indent, so it stays aligned with the names by construction.

Stacking replaced a single flowing line, where the second team started
wherever the first one happened to end. It also removes the "at" / "vs", so
the order carries that meaning: away team first, except in soccer, which is
written home side first. A neutral site says so on the detail line, but only
when nothing else would -- bowls and tournament rounds already name themselves.

Both columns take their line height from one custom property, `--line-h`, and
the time and network are laid out identically -- blocks whose line box is one
team line tall. That is what keeps them level with the records beside them:
measured, 0.3px out on a phone and exact at desktop width. A time with nothing
under it centres against the pair instead of sitting on the first.

## Names

**`team-names.json` is the source of truth where it names a team.** ESPN's name
on the left, the name to print on the right, keyed by league so two sports can
disagree about the same school. It is a separate file rather than a corner of
`config.json` precisely so other tools can read it -- the standings page uses
the same table, either from this folder or from the repo's raw URL. It must
live inside the repo: the daily build runs on GitHub Actions and cannot see
anything else on the machine.

What it covers:

* **NFL, MLB, NBA, NHL** -- full city and nickname ("Detroit Tigers", not
  "Tigers"). These are identity mappings; they exist to be edited.
* **MLS** -- the full club name, with FC/SC/CF dropped only where the club is
  still two words without it. Austin FC, Charlotte FC, Nashville SC, Toronto
  FC, FC Dallas and CF Montreal keep theirs because dropping it leaves one
  word. LAFC is "Los Angeles", Red Bull New York is "New York Red Bulls".
* **College** -- acronyms spelled out (Louisiana State, Southern Methodist,
  Southern California) except UCLA, UAB, UNLV, UTEP, UTSA, NJIT and RIT.
* **EPL and Europe** -- United/City/Town/Albion kept, club-type words dropped
  (AFC Bournemouth is Bournemouth, VfB Stuttgart is Stuttgart, AS Roma is
  Roma). `Sporting CP` keeps its, by choice. A few are named outright:
  Copenhagen, Inter Milan, Athletic Bilbao, Union Saint-Gilloise.

**Accents are always stripped** -- Atletico Madrid, Malmo, Bodo/Glimt, Leon.
`filters._plain()` decomposes and drops the combining marks, which handles
most of Europe, and names by hand the letters that carry their sound in the
glyph rather than in a mark (o-slash, ae, eth, thorn, l-stroke, eszett), since
those decompose to nothing. It runs on every label, so a club that is not in
the table is covered too.

Anything the table does not name falls back to the rules below.

College and club teams are named by `location` ("Boise State", "Crystal
Palace"), because ESPN's `shortDisplayName` abbreviates exactly the part that
identifies them -- "Boise St", "C Palace", "Nottm Forest". Pro teams are the
other way round: `short` is the nickname ("Tigers") and `location` is the
city, so the preference only flips for college and soccer. A trailing FC, CF
or SC is dropped, since every club on the page is a football club.

`team_names` overrides the label outright -- Ajax Amsterdam is just Ajax,
Tottenham Hotspur is Tottenham.

**Names are never shortened.** Two schemes were built and both removed.
Abbreviations went first: CRY, BHA and NFO are unreadable, and a threshold low
enough to catch the real offenders turned a quarter of the page into
three-letter codes. Swapping in ESPN's short name lasted longer, and measured
widths beat counting characters ("Crystal Palace" is fourteen characters and
81px, "Michigan State" is fourteen and 86px) -- but the whole approach was
wrong in principle, because the decision happens at build time and cannot know
the reader's screen. The budget was worked out for a 375px phone, so on any
wider one it condensed names that had room to spare. A name that genuinely
does not fit now **wraps**, which costs a line only where it is really needed
and never has to guess.

## Scores

Once a game starts, the score takes the record's place beside each team --
where a scoreboard puts it, and the thing worth reading by then. The status
column carries only the state: ESPN's own line while it is on ("Bot 1st",
"9:45 - 2nd"), then "Final".

The score is read **per team**, never built as one string. Soccer prints the
home side first and every other sport away at home, so a combined "1-4" has to
know the print order -- and when it did not, every soccer result was reported
backwards for months. A score attached to its own team cannot be flipped.

**The losing team is struck through**, dimmed as well since a line alone is
easy to miss at this size. A draw has no losing side, so the word **Final** is
italicised instead.

Putting the score beside the status was tried and rejected: it reads well for
baseball ("Bot 1st 0-0") but the NFL's status is already "12:10 - 2nd", and
with a score that needs 82px in a column that holds 74.

## Betting lines

The line sits against the team it is about -- "Indiana (-40.5)" -- never
trailing the networks. Which team that is comes from ESPN rather than from
parsing the provider's abbreviation: point-spread sports flag the favourite
per side, and `spread` is signed from the home team, so the favourite always
reads as minus its magnitude.

**A point spread always carries a decimal place**: "-7.0", not "-7". Beside
"-7.5" the two read as different kinds of number otherwise, and `%g` was
quietly dropping the trailing zero. Moneylines are whole by nature and keep
none.

**Soccer has neither field.** Its `details` string holds either a three-way
moneyline ("LIV -205") or an Asian handicap ("TOT -0.5"), and names the team
by an abbreviation -- which does match ESPN's own, verified across 33 priced
fixtures. Only the moneylines are shown, labelled **ML** so they cannot be
read as points; a moneyline is 100 or more in magnitude, a handicap always
less. Where the scoreboard offers only a handicap, the core API carries every
provider and the full market, and that fallback fires about twice a fortnight.
A provider is trusted only when it prices **both** sides -- one price alone
cannot tell a favourite from an underdog.

## Live scores

The build sets the slate; the page keeps the numbers current. ESPN's API sends
`Access-Control-Allow-Origin: *` and `cache-control: max-age=6`, so the browser
can ask it directly and the data is fresh to within seconds. **No Actions run,
no deploy, no server cost** -- which also means it keeps working on a morning
when the scheduled build does not.

Every row carries `data-game`, `data-path` and `data-state`, and each side's
name and score cell carry `data-side`, so the script can find the two halves of
a row without depending on their order in the grid.

**A game on now is bold.** That is keyed off the row's `data-state` rather
than a class of its own, so the live script bolds and unbolds it simply by
updating that attribute as a game starts and finishes.

What it does: while the tab is **visible**, every **60s**, for the rows in
**today's panel that are not already final**, one request per league (not per
game), patching the status, the two scores, the strikethrough and the
italicised draw.

**It can never change which games are listed.** The filters run at build time
against standings and odds, so a game that becomes interesting at 3pm still
will not appear until the next build. Porting those to JavaScript is a far
bigger job and was judged not worth it.

**Failure is silent by design.** The fetch is wrapped, and on any error the
page simply keeps the build's numbers -- exactly what it showed before any of
this existed. Worth knowing which risk is which: the API changing breaks the
morning build too, so that is not new; CORS being withdrawn would break only
this, and only back to today's behaviour.

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
not need both. `network_names` settles the spellings ESPN alternates between:
it returns "SECN+" on some games and "SEC Network+" on others, and the short
forms are what fit the phone's 84px column. MLB.TV is flagged *national* despite being a streaming service,
so `hide_networks` still does real work, as does hiding `Universo` and `TUDN`.

## The five sections

Fixed order, and a section with no games is not drawn:

**Main Slate** — your teams. **Highlights** — directly under it, holding three
things:

* the rivals -- Ohio State, Michigan State, Notre Dame, Arsenal, Chelsea
* your own teams whose games are not, in themselves, an event: the Tigers,
  Pistons, Cavaliers, Red Wings, Atlanta United and Cornell (`highlight_teams`),
  who move up to Main Slate once they reach a postseason
* every European club fixture -- the Premier League, both domestic cups and all
  three UEFA competitions (`highlight_all`)

**Football**

* ranked college football in the regular season
* the CFP in full
* a bowl only if it has a Big Ten team, a ranked team, or Power Four on both
  sides -- the rest of the bowl slate goes to National
* the NFL's standalone windows, and its playoffs

**Basketball**

* ranked college basketball in the regular season
* the NCAA tournament, the NIT and the Crown. No ranked test is needed: in the
  bracket ESPN puts the **seed** in the rank field, so every tournament game
  reads as ranked anyway

**National** runs in **two halves**, with a gap between them the same height as
the one between a heading and its card. The lead half holds the games that are
an event in themselves; the second holds the ordinary nightly slate:

| half | what is in it |
| --- | --- |
| lead | college football, college basketball, college hockey, the NFL, and the MLB/NBA/NHL/MLS **postseasons** |
| second | MLB, NBA, NHL, MLS and the Leagues Cup otherwise |

Each half is in start-time order; that listed order only breaks a tie between
two games starting the same minute. The second card is drawn only when it has
something in it, and takes the gap only when something sits above it.

**Soccer has no postseason flag** -- ESPN files the MLS bracket as regular
season -- so MLS Cup would otherwise sort beside a Wednesday night. Rounds that
count are named per competition and tested by `is_event_round()`, shared with
the rule that promotes a demoted favourite to the Main Slate. The Leagues Cup
is checked before it: its knockouts are named rounds, but the competition
belongs in the second half.

It mixes sports, so every
row here names its competition, and the pro leagues say why they are there:
`NBA - National TV`, `NFL - Playoff Race`. A row whose round already names
itself (`CFP Semifinal`, `NCAA Hockey - Regional Final`) is left alone.

It holds the playoff races, the MLB/NBA/NHL/MLS postseasons, unranked college
football and basketball, the minor bowls, the NCAA hockey tournament, the
non-European cups -- and **national broadcasts**, which is the one rule that
puts games on the page that nothing else would: about 1.3 a night in MLB, 2.3
in the NBA, 1.1 in the NHL.

**A national broadcast cannot be read from ESPN's `national` flag.** It marks
every NHL game, because ESPN+ carries all the out-of-market ones, and MLB.TV
likewise. `NATIONAL_TV` in `filters.py` is an explicit list instead, written
the way `_flat()` leaves a name -- lowercase, no spaces -- because that is what
it is compared against. "apple tv" in that set would never match anything.

**Postseason promotes the demoted teams back to Main Slate.** A Tigers game in
June is a highlight; a Tigers playoff game is the main slate.

**`highlight_all` never demotes your own team.** Tottenham is on the Main Slate
wherever they are playing -- league, cup or Europe -- and it is the *rest* of
European football that sits in Highlights.

| team | where |
| --- | --- |
| Lions, Michigan, Tottenham, USMNT | Main Slate, always |
| Tigers, Pistons, Cavaliers, Red Wings, Atlanta United, Cornell | Highlights, Main Slate in the postseason |

Soccer has no postseason flag, so a competition names the rounds that count
(`promote_rounds`): the MLS bracket and MLS Cup, the Leagues Cup knockouts, and
every Concacaf Champions Cup round, since that is a straight knockout. The U.S.
Open Cup stays in Highlights throughout, deliberately.

In **Main Slate** the league is not named, since the team implies it -- except in
soccer, where Tottenham and Atlanta United appear across half a dozen
competitions and the badge is the only way to tell the Carabao Cup from the
league. **College hockey always names itself**, wherever it lands.

**Lopsided games are dropped** from the ordinary sections: college football
over **30** points, college basketball over **15** (`max_spread`). Three things
survive it -- Syracuse always (`spread_exempt_teams`), college football's four
Saturday marquee windows, FOX at noon, CBS at 3:30, NBC and ABC at 7:30
(`spread_exempt_windows`), and anything in Main Slate or Highlights, which the
rule never touches. On the 2026 opening Saturday that took college football
from 26 games to 14.

Window times allow an hour either side (`spread_window_minutes`): the slots
drift a quarter-hour week to week, ABC's primetime moves between 7:30 and 8,
and a weather delay can push a start further still. Each network has one game
in its window, so the tolerance costs nothing.

**Odds only exist for upcoming games.** ESPN strips them from completed ones,
so the rule shapes the fortnight the app actually shows and quietly does
nothing when you browse a past date. A game with no spread is always kept.

## College hockey is three teams and a bracket

Michigan on the Main Slate, Cornell in Highlights, and the NCAA tournament.
Nothing else -- `only_my_teams_outside_postseason`.

**Its conference tournaments cannot be told from the regular season.** ESPN
files them as season type 2 with no round and no headline, so they are treated
as regular season and only Michigan and Cornell appear. Only the NCAA
tournament carries the postseason flag: 15 games, regionals and the Frozen
Four, all at neutral sites.

**The FCS bracket is excluded** (`postseason_top_division_only`). College
football's blanket postseason rule would otherwise admit it alongside the
bowls -- Montana against Montana State on a December Saturday. Membership of
the top division comes from the core API, since the teams endpoint ignores
`?groups=`.

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
- **Two things that must line up need the same layout mechanism.** The time
  was a flex box with its text centred; the network, after a clip guard was
  added, was a block with a line height. They therefore sat on different
  baselines -- one 2.4px above the record beside it, the other 1.3px below --
  and no single nudge could fix both. Laying both out identically (a block
  whose line box is one team line tall) puts them within 0.3px of the record
  on a phone and exactly on it at desktop width, with no nudge at all. A `top`
  offset that "fixes" an alignment is usually covering for something like this.
- **Compare against the neighbour, not the thing you happened to pick.** The
  time sits beside the *record*, not the team name, and those are different
  sizes on different baselines. Aligning to the name left it visibly off
  against the record, which is what a reader actually sees.
- **Measure glyphs only after `document.fonts.ready`.** A reading taken before
  Source Sans 3 arrived described the fallback font and was out by 1.4px, which
  shipped as a correction that pushed the time visibly low.
- **The score has to follow the order the teams are printed in.** It was built
  away-home for every sport while soccer rows are written home side first, so
  every soccer result read backwards -- Inter Miami's 5-1 showed as 1-5. It
  went unnoticed because odds and scores only coexist on past dates.
- **A page that is left open never refetches.** An installed app resumed from
  the home screen shows its last render for as long as the phone keeps it
  alive; a desktop tab restored from the back/forward cache does the same. The
  service worker is network-first, so a real load always got fresh content --
  there just was not one. The page now carries the day it was built for and
  reloads on `visibilitychange` or `pageshow` if the date has moved on or it
  has been hidden half an hour. Two hooks, because a bfcache restore fires no
  `visibilitychange` at all.
- **Scheduled runs can stop without any error.** No run of any kind was
  created in any of the three repos on 2026-08-27 -- not scheduled, not from a
  push -- while the workflows stayed `active`, Actions stayed enabled, the
  crons were untouched and `workflow_dispatch` worked every time. Nothing
  reports this: the last green run just sits there. Compare `gh run list`
  against `git rev-parse HEAD`, and re-fire with
  `gh workflow run "Build and publish" --ref main`.
- **A build-time decision cannot know the reader's screen.** Anything sized
  against a viewport -- shortening a name to fit, say -- is a guess that is
  wrong for every phone that is not the one you picked. Let CSS handle it.
- **Measure baselines, not box centres.** Centres matched exactly while the
  text still read as misaligned; a zero-size inline-block appended to an
  element sits on its baseline and gives the number that matters.
- **A flex `gap` disappears when the container stops being flex.** The narrow
  stylesheet makes the name cell a block, so the gap between a name and its
  betting line vanished on phones while looking right on desktop. It is a
  margin now, which works in both.
- **A nested "phone" panel cannot honour a viewport media query.** A 375px box
  inside a desktop page still gets the desktop rules, so a mock built that way
  shows truncation that a real phone would not. Duplicate the rules scoped to
  the panel, or open the page at a real width.
- **Team crests need the dark variant.** ESPN's default logo is drawn for a
  light background: measured on canvas, the Tottenham badge averages luminance
  35 and Ohio State's 52, both invisible on a #16161a page. Swapping `/500/`
  for `/500-dark/` gives 255 and 165. Every league tested returns 200 for the
  variant, and an `onerror` swap covers any team that does not.
- **...but the dark variant is not always right either.** For some clubs it is
  a flat white silhouette -- Liverpool and Tottenham both measure saturation 0,
  luminance 255, so at 20px they are the same shape twice. `python logos.py`
  decodes both 500px variants in pure Python and writes `logo_overrides` into
  `config.json`: 77 teams whose default variant reads better (the Dodgers,
  Tigers, Phillies, Raptors, Steelers, plus Liverpool, Alabama and Michigan
  State via the hue rule below). Measurements are cached in
  `output/logo-measurements.json`, so a re-run after adding a league is quick.
- **Brightness alone is the wrong test; hue decides.** A crimson A or a purple
  note reads perfectly on #16161a, while a navy crest of the same luminance
  vanishes. So when neither variant clears the brightness bar, the mean colour
  of the default one decides: near-neutral (black or grey) and navy keep the
  white silhouette, anything else takes the coloured variant. Navy runs
  r < g < b (0c2340, 132448) and purple runs g < r < b, so the two are told
  apart by that ordering rather than by hue angle.
- **Only FBS, FCS and Division I are measured.** ESPN returns 759 college
  football teams, mostly Division II and III schools no rule here could
  surface. The teams endpoint ignores `?groups=`, so the ids come from the core
  API instead: `.../seasons/{y}/types/2/groups/{80,81}/teams` for football and
  group 50 for basketball. That takes 759 down to 277.
- **A few crests are palette PNGs** (colour type 3) -- Rochdale, Strasbourg --
  and one is a GIF served with a `.png` name (Newport County). The decoder
  handles 8-bit palettes by expanding them through PLTE and tRNS; 4-bit ones
  and the GIF return None and the team keeps its dark variant. Failed
  measurements must not be cached as a result, or fixing the decoder changes
  nothing on the next run.
- **22 teams read badly in both variants, and are left alone deliberately.**
  A pale disc behind them works, and was built and rejected: only ~3% of teams
  would carry one, so it reads as a mistake rather than a style, and the row
  shows one crest on a disc beside one without. Making it uniform is not
  possible either. ESPN's pre-composited files (`primary_logo_white`,
  `primary_logo_on_primary_color`) are 4096px and 150-270KB each -- 80 to 160
  crests a page, so 16-32MB for images drawn at 20px -- and the CDN ignores
  resize parameters. Compositing the `dark` variant onto the team colour
  instead fails because that variant already carries colour for 1,594 of the
  1,752: it puts the Red Wings' red wheel on a red disc. So these 81 stay as
  they are, which is no worse than before.
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

Three UTC slots fire and a gate job lets exactly one through: 6am Eastern
normally, with the 7am and 8am slots acting as **catch-ups**. They are needed:
GitHub queues scheduled runs rather than guaranteeing them, and on the first
real morning the 6am cron ran **64 minutes late**. A catch-up only builds if
`output/history/_last_build.txt` -- committed by the build itself -- does not
already show today, so the page is still built exactly once a day.

In practice the page updates between 6 and 8am Eastern, usually nearer 6.

If a league or the odds feed cannot be reached, the page says so in a quiet
line at the top of today rather than looking like a quiet day.

The history commit carries **`[skip ci]`**: without it, the push retriggers the
workflow, which commits again, forever.

Trigger a build by hand from the Actions tab, or by pushing anything.

## Environment

Python 3.12.10 win-arm64, stdlib + `requests` + `openpyxl` (template only).
**No pandas or numpy** — Smart App Control blocks numpy's ARM64 binaries on
this machine and that is not worth relitigating; see the dynasty README.
