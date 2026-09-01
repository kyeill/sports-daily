
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
| NFL, MLB, NBA, NHL, MLS | my team, a playoff race, or a playoff game |
| College football, basketball | ranked, Big Ten, a rival, or Syracuse |
| College hockey | Michigan, Cornell, or the NCAA tournament |

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
