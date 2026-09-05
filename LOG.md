
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

## 2026-08-29 (later still) — draws mark the teams, not the word

A drawn game used to italicise "Final". Both team names now lean instead, so
the outcome sits where you are already reading -- and among rows whose losers
are struck through, "both leaning" reads as a different result at a glance in
a way that one italic word did not. Done in the build and in the live script
by the same rule, so a game drawn while the page is open looks like one that
was drawn before it loaded.

Checked against three real draws (Brentford 1-1 Liverpool, Everton 2-2
Brentford, Burnley 1-1 Chelsea): both names carry the class, neither carries
the loser's, and no `<em>` is emitted anywhere.

## 2026-08-30 — Premier League matches in National

A standalone Saturday match, or a standalone Sunday match kicking off at
11am ET or later, now appears in National when no other rule has claimed it.
Roughly two a month: 17 across the whole 2025-26 season, out of 114
standalone matches, the other 91 being ones the existing rules already show.

**Nothing already shown moved.** Swept the full season before and after:
266 matches kept before (38 Main Slate, 228 Highlights), 283 after (38, 228,
plus 17 National) -- zero changed section, zero disappeared.

The mechanism is a new `national_rules` block on a league's `include`, kept
deliberately separate from the ordinary `rules`. Those feed the tier, and EPL
carries `highlight_all`, which sweeps everything they match into Highlights --
precisely the catch-all these have to sidestep. A match qualifies only when
nothing else claimed it, stays tier "interest", and so files under National.

`from_hour` is a floor on the local kickoff rather than a named slot: Britain
and the States change their clocks on different dates, so the early Sunday
match drifts between 9:00, 9:30 and 10:00 Eastern across a season. The floor
turns away six matches a season, all of them that early kickoff.

EPL falls in National's **lead half**, which is what `national_bucket`
returns for any competition it does not name.

## 2026-08-31 — USA Network spelled out

`USA Net` is ESPN's own short name; the page now prints `USA Network`.
Measured at the phone's 12.5px after the webfont loaded: 68.5px against the
74px the column allows, so it fits with 5.5px to spare -- but it is now the
widest thing in that column, where the time used to set the width. Anything
longer would need a short form in `network_names`, as ACC Network and CBS
Sports Network already have.

## 2026-08-31 (later) — ACC Network and SEC Network spelled out too

Their `ACCN` / `SECN` renames are gone, so ESPN's own names print in full.
Measured at 12.5px with the webfont loaded, against the 74px the column
allows: ACC Network 67.7px, SEC Network 67.5px, both clear.

The rest stay short because they do not fit: CBS Sports Network 104.7px,
ACC Network Extra 96.3px, Big Ten Network 85.3px (never renamed -- ESPN calls
it BTN already), and SEC Network+ at 73.7px, inside the budget by 0.3px and
so not worth trusting to a different font stack.

## 2026-08-31 (later) — UConn reads as Connecticut

Added `"UConn Huskies": "Connecticut"` to `team-names.json` for all three
college sports UConn plays -- football, basketball and hockey -- following
the same pattern as BYU, LSU, SMU and the rest. The hockey section had been
empty until now.

Checked against a real fixture: Maryland at UConn on 2026-09-12 renders as
"Maryland" and "Connecticut".

## 2026-08-31 (later still) — grey standoffs, orange marquee windows

**Two of the named clubs against each other now takes the rival grey.** A
Manchester derby, or either against Liverpool, had been falling to the home
side's colour -- the same "no honest pick" the two-rivals case already
answers with `RIVAL_GREY`. Only clubs named in `tint_prefer_teams` count: an
all-English tie in Europe is a weaker coincidence and still takes the home
side, as before. Verified on all three head-to-heads in the season.

**The showcase windows print their network in the rank blue.** New
`marquee_windows` on a league, matched on network AND kickoff together:
college football's FOX noon, CBS 3:30 and NBC 7:30 on Saturdays, and the
Saturday Premier League match on NBC. Bounds are ranges, not times, because a
window can shift and because the two countries change their clocks on
different dates.

Measured over the 2025 season before choosing them. It lights 61 games and
correctly leaves alone FOX's own Saturday 3:30 window (11 games), NBC's 3:30
(3), CBS's 7:30 (3), every Friday game, and the Premier League's Sunday NBC
matches. The one judgement call is a 7:00 PM NBC kickoff, caught by the
wiggle room on the 7:30 window.

## 2026-08-31 (later still) — marquee networks are blue, not orange

Switched `.nets.marquee` from `--accent` to `--rank`, the same #8fb0d8 the
rank numbers use. Verified in the page that the two computed colours are
identical, so a marquee network and a team's rank read as one signal rather
than two.

## 2026-09-01 — grey as the default, and the trio back their opponent

**Grey is now what a game gets when nothing in it is worth rooting for**,
rather than the home side's colour by default. A league declares what saves
it, via `tint_grey_unless`:

| League | Saved by |
|---|---|
| Premier League, the English cups, UCL/UEL/UECL | nothing beyond the big six (or an English club in Europe) |
| NFL, MLB, NBA, NHL, MLS | my team or a playoff race -- a playoff *game* does not save it |
| College football, basketball | ranked, Big Ten, a rival, or Syracuse |
| College hockey | Michigan or Cornell |

Absent means the league never greys out; an **empty list** means nothing
beyond the names already checked can save it. The two are different, so the
test is for absence, not emptiness -- an empty dict would have read as
"never grey" and quietly disabled the whole rule.

Bowls deliberately do **not** get the postseason exemption: the rule is that
unranked and not-Big-Ten goes grey, and most bowls are exactly that. The CFP
is unaffected because those teams carry a rank.

**Liverpool, Manchester City and Manchester United now back their opponent**
in the Premier League and the English cups -- watched the way a rival is,
where the interest is in who can beat them. In Europe they keep their own
colour, which they reach through `tint_prefer_clubs_from` rather than the
named list, so the two cases stay separate. Verified: Forest v Liverpool
takes Forest's red, Ipswich v United takes Ipswich's blue, while in the
Champions League Leverkusen v City stays City's blue and PSV v Liverpool
stays Liverpool's red.

## 2026-09-01 (later) — playoff games grey out too

Dropped the postseason exemption from the five pro leagues and college
hockey. A playoff run you are not in is still someone else's, so an NFL
playoff game, a World Series game or an NCAA hockey tournament game without
Detroit, Michigan or Cornell now greys out like any other. Verified on real
brackets across all six competitions.

`tint_grey_unless` still understands `"postseason"`; nothing asks for it.

Kyle noted he may revisit this later -- possibly colouring by sport rather
than defaulting to grey.

## 2026-09-01 (later still) — Tigers in navy

`Detroit Tigers` overridden to **#0a2240**, which is ESPN's own primary; the
orange it replaces was the override put in because the navy trips
`invisible_colour`. An explicit `team_colors` entry outranks that test, so it
applies as written.

It is faint by design of the palette, not by accident: 1.04:1 against the
card. The Penn State override already in use (#061440) sits at 1.07:1, so
this is no worse than something already accepted. A lighter navy (#1c3f6e)
would read at 1.57:1 if it ever wants raising.

Ipswich has no usable alternate: ESPN offers only #F5F2DC, a cream that
`washed_out` rejects, so it would be swapped straight back to the blue.

## 2026-09-01 (later still) — Ipswich to a truer blue

`Ipswich Town` overridden to **#3a64a3**. ESPN gives #0000fa, a pure
electric blue; there was no alternate to take instead, since the only one on
offer (#F5F2DC, cream) is rejected by `washed_out` and would have been
swapped straight back. The override reads at 2.79:1 against the card, against
1.88:1 for the ESPN blue, and passes both the invisible and washed-out tests.

## 2026-09-01 (later still) — three club colours, and a way to write to the Sheet

ESPN gives Everton, Brighton and Crystal Palace virtually the same colour
(#0606fa, #0606fa, #0202fb), so on the page they were indistinguishable, and
the alternates were no help: Everton's is white and Palace's black, which the
washed-out and invisible rules reject, and Brighton's teal is not a club
colour. All three now carry overrides -- Everton #003399, Brighton #0057b8,
Crystal Palace #1b458f.

**The Colors tab can now be written to.** It is the master list -- three sites
read it and it is merged OVER config.json -- but Google's CSV endpoint only
reads, so every colour had to be pasted in by hand. `doGet` in
`k-money/apps-script/reminders.gs` (the script bound to that Sheet) gained a
`color` action, guarded by a token kept in Script Properties rather than in
the repo, and `set_color.py` here calls it:

    python set_color.py "Everton" 003399

It writes config.json either way, so a missing or broken endpoint cannot lose
the colour -- it prints the row to paste instead. The script forces the cell
to plain text before writing, which stops Sheets eating the leading zero of an
all-digit value: that is exactly how Penn State's 061440 became 61440.

Needs `secrets.json` (gitignored) with `colors_endpoint` and `colors_token`,
and the script redeployed as a web app.

## 2026-09-01 — soccer shows a chosen team's price, not the favourite's

Which number a soccer row carries is now decided by WHO is playing rather
than by who is favoured: the favourite's line says nothing about your own
team when they are the underdog.

| Situation | Shows |
|---|---|
| Tottenham, Atlanta or the USMNT playing | their own price, always |
| Tottenham vs a Top Six club | Tottenham's double chance |
| Atlanta / USMNT | double chance only when it is >= +100, else moneyline |
| Arsenal or Chelsea vs anyone else | the OPPONENT's double chance |
| Arsenal vs Chelsea | left alone -- no opponent to back, and neither is mine |

Top Six is Arsenal, Chelsea, Liverpool, Manchester City, Manchester United:
five clubs, because Tottenham is the sixth and never its own opponent.

Double chance is win-or-draw, two outcomes of three, so the implied
probabilities add: `1/((1/a)+(1/b))`, which reduces to `ab/(a+b)` in decimal
odds. Both derivations are cross-checked in `espn.double_chance`. The book's
margin rides along in both legs, so it sits slightly shorter than a quoted
double chance -- it is derived from the three-way market, not published.

**The draw price is not in the scoreboard.** `espn.three_way()` reads the core
API and takes the first provider pricing all three; a provider missing the
draw is skipped rather than topped up from another, which would blend two
books' margins into one number. In practice that is DraftKings; Bet 365 often
omits the draw. Called only for games already being kept, so it costs a
handful of requests per build, cached three hours.

ESPN prices about two weeks out, so more distant fixtures have no three-way
market and keep whatever the scoreboard gave. Labels are `+289 x2` and
`+185 ML`.

## 2026-09-01 (later) — the favourite for Arsenal v Chelsea, and rounder x2

Arsenal against Chelsea backs neither side, so the row now shows the plain
favourite's moneyline. It is read from the same three-way market as
everything else rather than from whichever single leg the scoreboard happened
to carry, so it is right whichever of them is at home.

Double chance is rounded to the nearest five. The last digit of a price
worked out from three others is arithmetic, not something anyone is
offering: +174 became +175, +112 became +110, -102 became -100. Quoted
moneylines are the book's own numbers and are printed exactly as given.

## 2026-09-01 (later still) — every price to the nearest five

Moneylines are rounded like the double chances now, in all three places one
can come from: the scoreboard's own `details`, the core-API fallback, and the
soccer rules here. Books quote moneylines in fives anyway, so it rarely moves
a number -- the ones it does move are those converted from a provider's
decimal or fractional price, where +383 and -141 were arithmetic artefacts
rather than anything on offer.

Point spreads are untouched: a half-point line is a real half point.

## 2026-09-03 — Week 0 retired, and expiry dates that actually expire

**The Week 0 rule is gone.** `power_conference_extra_days`/`_dates` admitted
unranked Power-Four-vs-Power-Four on the Saturday of 08-23..08-29, when Week 0
was the only thing on. 2026 was the last Week 0, and those dates are MM-DD, so
left in place the rule would have fired every August afterwards against a
normal week's card. The mechanism stays in `filters.py`; nothing sets it.

**`expires` now works from config.json.** It had only ever been honoured on
the Sheet path, so an entry written straight into `config.json` carried its
expiry as decoration and stayed for good. `filters.watchlist_for` now drops
expired entries, which is what makes a season-long interest safe to write
down: it stops following the team on its own instead of waiting to be noticed
a season late. Read against today, not the day on screen, so browsing back to
November does not resurrect somebody since dropped. An unreadable date keeps
the row and says so.

## 2026-09-04 — delayed games say how far they got, and postponed ones stop lying

**A delay now reads `Delay - 1st`.** ESPN keeps a delayed game at state "in"
and buries the period in its own prose -- `STATUS_RAIN_DELAY`, shortDetail
"Rain Delay, Top 1st". The reason does not matter; how far in it got does.
Matched on `"DELAY" in type.name`, which covers `STATUS_RAIN_DELAY` and
`STATUS_DELAYED` alike, with the period taken from `status.period`.

Each sport names that period its own way -- innings and hockey periods as
ordinals, football and the NBA in quarters, soccer and college basketball in
halves, overtime beyond regulation and extra time in soccer. The live script
carries the same table, keyed off the row's league path, so a game that goes
into delay while the page is open reads the same as one built that way.

Verified against a real Tigers-Guardians rain delay caught live: ESPN's
"Rain Delay, Top 1st" renders as "Delay - 1st".

**Postponed games no longer read as "Final".** ESPN files them as state
"post", so they were showing as finished -- and carrying 0-0, which the draw
rule then italicised as a draw on a game nobody played. They now show ESPN's
own word ("Postponed") and carry no score, no loser and no draw. Cancelled
and suspended games are treated the same way. Rare -- three across a season's
sweep -- but wrong every time it happened.

## 2026-09-04 — gviz guesses the header depth, so pin it

`gviz/tq?tqx=out:csv` decides for itself how many leading rows are header, and
when it decides more than one it does not skip them — it **merges them into a
single space-joined row** and returns that as the header. Those rows are then
missing from the read while sitting untouched in the Sheet.

The guess is driven by column type, so it changes as the DATA changes. A tab
that has read correctly for weeks starts dropping rows the moment a column
gains a value of a different kind. It cost k-money six of eight tasks the day
two were ticked and dates landed in a previously empty Done column.

`&headers=1` pins it, and is now on `GVIZ` in `sheets.py`. The Teams and
Options tabs each have exactly one header row, so there was never a reason to
let it guess. Nothing here had gone wrong yet — this is the same latent bug,
fixed before it fired.

## 2026-09-04 (later) — the blowout filter was dead on every past day

ESPN deletes the odds the moment a game goes final, so `_spread_points`
returned None for everything already played and `is_blowout` never fired
again. Games filtered out on the day quietly came back once they were over --
on yesterday's tab that was Idaho 14-66 Utah, Arkansas-Pine Bluff 14-54
Missouri and Eastern Illinois 7-59 Minnesota, three of the eight games kept.

The final margin now stands in when the line has gone. It answers the same
question with better evidence: before the game the spread is a forecast,
after it the score is the fact. Measured across nine days, it changes exactly
one of them -- dropping exactly those three -- and adds nothing anywhere.

Note the rule still only bites at build time, so a game kept this morning
stays on today's tab all day however it ends; it is tomorrow's build, seeing
it finished, that leaves it out.

## 2026-09-04 (later still) — Arsenal and Chelsea only hand the number over when beatable

Their opponent's double chance is now shown only while Arsenal or Chelsea are
the underdog of the two. Favoured, they take their own moneyline back: the
point of backing the other side is that somebody might beat them, and against
a 6.00 outsider nobody is about to.

The comparison is between the two teams, not against the draw, so a short
draw price cannot make both of them underdogs at once.

In practice this hands the number back most weeks -- all five priced fixtures
in the current window have them favoured, including at Napoli in the
Champions League. The opponent's double chance now appears only when it means
something.

## 2026-09-05 — the italic lean was being shaved off

A drawn game's names are italic, and the d of "Newcastle United" was losing
its tail on tablet. A flex item is sized to the text's ADVANCE width, which
for an italic excludes the part of the last glyph hanging past it, and
`overflow: hidden` on the name cell then clips exactly that overhang. It only
ever showed above 640px because the phone layout sets the cell to
`overflow: visible`.

`.t.drew` now carries `padding-right: 0.16em` with an equal negative margin:
the padding widens the clip box, the margin gives the space straight back to
the layout. Measured: the box goes from 106px to 108px around a 106px name,
so the lean has 1.9px to land in where it had 0.08px -- and across 113
positioned elements on the page, nothing moved.

Note the DOM cannot see this: `getBoundingClientRect` reports the advance
width, not the inked extent, so the overflow measures as zero either way. The
screenshot was the evidence.

## 2026-09-05 (later) — orange for the marquee windows, blue for what is on now

The two colours swapped jobs. The showcase network windows go back to the
accent orange (#e0834f -- the same colour K Money's Church tab gives its
headings), and a game actually in progress takes the blue the ranks use, so
"on now" reads at a glance instead of merely being bold.

**And an upset watch.** When a ranked college side is losing to, or level
with, one nobody fancied, BOTH scores turn orange -- an upset is a fact about
the game, not about one team. The underdog is whoever is unranked, or ranked
further down; two exceptions, both his: Michigan State or Ohio State doing the
upsetting is not a result to celebrate, and neither is Michigan being on the
wrong end of one. Michigan doing the upsetting still counts.

Eligibility is settled at build time and written onto the row as
`data-upset`, because ranks and team names do not change mid-match. Only the
comparison of the two numbers is left to the live script, which is the only
part that changes while you watch.

### The rankings were already right

Checked rather than assumed, because the upset rule leans entirely on them.
`curatedRank` is not one fixed poll: for college basketball it is the AP poll
(matched 13 of 13 in a January week, against 7 of 13 for the Coaches Poll),
and for college football it follows the **CFP rankings** as soon as they are
published (12 of 12 in week 14, where AP managed only 8 -- Texas Tech 5th on
the committee's list and 7th on AP's, Oregon 6th and 5th).

So no work: the app already shows AP for basketball and switches to the CFP
list partway through the football season. Note ESPN's public `rankings`
endpoint never returns the CFP poll at all -- it is core-API only, id 21,
type `cfp` -- so anyone looking there would wrongly conclude it does not exist.

## 2026-09-05 (later still) — the 0-0 bug, and results that read at a glance

**The upset highlight was firing at kickoff.** Every game is level at 0-0
before anyone has done anything, and "level" counted, so each armed row went
orange the moment it kicked off -- which is where the orange on the Ohio
State, Indiana and Houston rows came from. It was never the build: all three
were correctly quiet there. A tie now needs somebody to have scored.

**Finished games say how they went.** Orange for a result worth seeing, grey
-- the same grey as a record -- for one that went the wrong way:

* orange: an upset; Ohio State or Michigan State beaten; Arsenal or Chelsea
  beaten or held. Cancelled when both sides are on the same list, since one
  of them losing is not news either way.
* grey: a loss by Michigan, any Detroit side, the Cavaliers or Cornell;
  Atlanta United losing or drawing; Tottenham losing, or drawing with anyone
  outside the top six -- a draw with one of those is a fair result.

Good beats bad where both apply, so **Michigan beating Ohio State reads
orange** rather than staying quiet.

Who is playing is fixed and only the result is not, so the rules resolve at
build time onto the row as `data-mood="good:home:L|bad:away:LD"`, leaving the
live script a comparison of two numbers and keeping one copy of the team
lists rather than shipping them to the browser. Twenty cases checked.
