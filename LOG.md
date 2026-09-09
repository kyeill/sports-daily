## 2026-09-09 (later, Highlights again) — hockey to the front, Cornell with his teams

College Hockey now leads `highlight_order`, ahead of the playoffs.

Two things came out of checking which of his teams actually reach Highlights,
over nine dates spanning the year:

- **The Lions, Tottenham and Michigan never do** — 2, 5 and 6 games in the
  sample, all Main Slate. Only the leagues carrying a `highlight_teams` entry
  demote a pinned team, and none of those three is on one.
- **The USMNT never does either.** Its four competitions carry no
  `highlight_teams`, so a pinned United States game stays on the Main Slate.
  Its rule is kept, since it was asked for and would start working the day that
  changes, but it cannot fire today. (Worth knowing for the next probe: without
  the Sheet, those competitions have no favourites at all — `team_group` is
  what lends them the USMNT, and it is applied when the Sheet is read. A local
  run makes those games look dropped when the cloud build pins them.)
- **Cornell always does** — 8 of 8. It sits with his own teams rather than
  behind the rivals in the college groups, which is what "my teams first, then
  rivals" means; without that a Cornell football game ranked behind Ohio State.

Verified with fourteen games on one minute: hockey, playoff game, Tigers,
Pistons, Red Wings, Atlanta, Cavs, Cornell football, Ohio State football, then
the basketball and soccer groups in their own orders.

## 2026-09-09 (last) — Highlights gets a cross-sport order

The tiebreakers added earlier ordered Highlights only within a sport, so an
Arsenal match and an Ohio State game kicking off together tied. `highlight_order`
is now one list read top to bottom, his own teams first and the rivals after:

    Playoffs > USMNT > Tigers > Pistons > Red Wings > Atlanta > Cavs
             > College Football > College Basketball > soccer

The rank is a pair — which rule, then where inside it — so "College Football
before College Basketball" and "Ohio State before Michigan State" are one
mechanism at two depths, and the sport orders written earlier are unchanged
underneath.

A rule naming only teams needs one of them present. A rule naming a league, a
sport or the postseason takes any game that fits, behind whichever teams it
also names: that is what keeps "Arsenal, then Chelsea, then any other soccer"
working now that soccer sits at the foot of a longer list.

"Playoffs" is `is_event_round`, not the `postseason` flag — soccer does not
carry one, and a competition names its own knockouts instead. Same test
National already uses for its leading card.

Verified with fourteen games forced to the same minute: they came out in
exactly that order. Start time still decides everything before the tie, and
finished games still sink; both re-checked.

**Not in the list, so last against a same-minute game:** Cornell, Michigan, the
Lions and Tottenham — they were not named, and all four do reach Highlights
sometimes, Cornell most often. College Hockey has no group of its own either.

## 2026-09-09 (later still) — tiebreakers for games starting together

Every section sorted on start time alone, so two games kicking off the same
minute fell in whatever order the leagues happened to be read. Each section now
says how to separate them, through `sort_key_for`:

- **Highlights** — Arsenal, then Chelsea, then any other soccer; College
  Football Ohio State, Michigan State, Notre Dame; College Basketball Michigan
  State, Ohio State, Notre Dame. Config, in `highlight_order`.
- **Football and Basketball** — the best rank in the game, lowest number first;
  a game with neither side ranked goes last.
- **National** — Soccer, College Football, College Basketball, NFL, MLB, MLS,
  NBA, NHL. MLS is named in its own slot rather than counting as soccer.

Only the tie is affected: the start time still decides everything before it,
and finished games still sink to the foot of their section. Both checked.
National's two cards still come first of all, which is not a tiebreak but the
card split itself.

**The console had drifted from the page.** `sections_for` exists so the two
cannot, and its docstring says as much — but `sports_daily.py` was building
Main Slate and Highlights by hand from a plain start-time sort and handing only
the remaining three sections over. So the page ordered Highlights correctly
while the console showed Chelsea last of five 10:00 kickoffs, which is how this
was noticed at all. It now passes every game through the splitter.

Unlisted competitions sort last against a game starting the same minute:
College Hockey in National, and anything in Highlights that is neither soccer
nor college football or basketball. Nothing was said about how the sports
compare inside Highlights, so those ranks can tie and the sort is left stable.

Still true in the console only: National's two cards print as one flat list, so
a leading-card game can appear above an earlier-starting ordinary one. The page
draws them as two cards with a gap. Pre-existing, untouched.

## 2026-09-09 (later) — a neutral stripe for all-Big Ten games

Two unranked Big Ten sides had nothing to separate them, and the stripe fell
through to the home team's colour — which says nothing about a game whose
interest is the conference rather than either side. They now take **`#0085ca`**,
the Big Ten's own blue.

The colour is sampled, not guessed: the conference logo
(`ncaa_conf/500/5.png`, id 5) is exactly two colours, `#0085ca` over 59% of the
opaque pixels and the wordmark over the rest. It reads well as a stripe at
4.12:1 against the row, and its hue keeps it clear of the `#9a9a95` that means
"nothing worth rooting for".

`_conference_neutral` sits on the fallback path, which is the whole reason
"not Main Slate or Highlights" needed no section test: a game claimed by one of
your teams or by a rival has already taken its colour and never reaches it.
Confirmed on real fixtures — Michigan v Rutgers and Michigan State v Michigan,
both all-unranked-Big Ten, stay in Main Slate in Michigan's yellow, and
Michigan State v UCLA stays in Highlights with UCLA's blue, because the rival
rule hands the stripe to the opponent.

Checked over three football Saturdays and three basketball dates: every
all-Big Ten game with two unranked sides turned blue, every game with a ranked
side kept the colour it had, and the controls — a Mountain West side against
UCLA, Cornell against Princeton — were untouched. Basketball needed no work of
its own; the rule keys on the conference, so leagues without one answer "" and
fall through.

## 2026-09-09 — Telemundo pushed Peacock off the derby

Manchester United v City on the 14th showed **Tele** rather than Peacock. ESPN
sends `["Peacock", "Tele"]`, and `Tele` is how it abbreviates Telemundo. The
streaming rule then did the rest: Peacock is on `streaming_networks`, which
exists so a game on NBC does not also say Peacock, so the moment any
non-streaming name is present it wins — and `Tele` counted as one.

`hide_networks` already carried Universo, Telemundo Deportes, TUDN and ESPN
Deportes. It never carried the bare `Tele`, which is the only spelling ESPN
actually sends.

Surveyed every national network name across all 21 competitions and seven
months first, rather than patching the one fixture. `Tele` appears 24 times and
`Univision` once; `Telemundo Deportes`, `TUDN` and `TUDN USA` never appear at
all. All three of `Tele`, `Telemundo` and `Univision` are now hidden.

Checked that hiding them can never blank a row: of the games carrying a
Spanish-language feed, **none** has it as the only national entry — 61 carry an
English one alongside. Re-run over the season, the 46 affected games now print
USA Network (26), Peacock (9), NBC (4), ESPN+ (3), NBCSN (2), Apple TV and
ESPN2. None is left without a network.

## 2026-09-08 — Porto in the other two European tables

`team-names.json` is keyed by competition, and `FC Porto -> Porto` was listed
only under the Europa League. Added to the Champions and Conference tables so
the club reads the same wherever it turns up.

Nothing on the page changes today: Porto plays in the Europa League this
season, where the short name was already being printed. What prompted this was
a fixture list in the conversation showing ESPN's raw names, not the app's.

Checked the rest of the tables for the same per-competition gap, a month at a
time because the scoreboard endpoint caps a long range at 100 events — 540
fixtures over the full European season, 36 clubs in each competition. No other
club is shortened in one table and left long in another.

## 2026-09-07 (night) — club membership by id, and Eintracht into National

Two things, both asked for after the last change.

**`clubs_from` matches ids now, like `both_clubs_from`.** It was matching
names, and the pool includes abbreviations, which collide across countries.
Measured against the competitions this app carries:

| code | on the continent | in England |
|------|------------------|------------|
| BRE  | Brest            | Brentford  |
| BAR  | Barcelona        | Barnet, Barnsley (FA Cup) |
| BOL  | Bologna          | Bolton Wanderers (FA Cup) |
| MIL  | AC Milan         | Millwall (FA Cup) |

So "a tie with an English club in it" would have counted Brest, and the FA Cup
pool makes it worse. Nothing had gone wrong yet — none of those clubs has been
in the European draw this season — which is exactly why it was worth fixing
while it was cheap.

Behaviour is unchanged where it currently matters: 67 European fixtures across
six matchdays, and names and ids agree on every one of them, both for the
`clubs_from` rule and for which side `tint_prefer_clubs_from` picks. Bremen was
checked directly too, and no longer counts as English (it never did — see the
correction below; the club that would have was Brest).

`clubs_in` is gone, having no callers left. `_club_names` stays for the league
table, which is keyed by name and has nothing else to match on.

**Eintracht moved from the tier rules to `national_rules`.** It lands in
National, and a rule that claims the game first still takes it higher, which is
what National rules do by construction. Checked over all six of its Champions
League fixtures: five in National, and Liverpool away in Highlights on the
English-side rule. A knockout tie goes to Highlights too, since the knockout
rule keeps every Champions League game at that stage.

## 2026-09-07 (evening) — the big-four ties, and Eintracht

National gains European ties played between Spain, Germany, Italy and France:
the Champions League at any stage, the Europa and Conference Leagues once the
knockouts start. In the 2026 league phase that is Juventus–Monaco,
Villarreal–Leverkusen, Inter–Dortmund and Inter–Atlético — matches that were
being dropped outright, since the league-phase rule only kept ties with an
English club in them.

`national_rules` now runs through `rule_matches` rather than testing the day
by itself, so a National rule can say "knockouts only" in the same words the
tier rules already use. `standalone` and `from_hour` stay its own, ahead of
that call. The Premier League's two rules are unaffected: verified across
standalone and non-standalone kickoffs on Saturday, Sunday before and after
the 11am floor, and a Monday.

`both_clubs_from` is the new condition — every side from one of the named
competitions, where `clubs_from` asks only that one side is. **It matches team
ids, not names.** The union of four countries collides with English clubs on
abbreviations. Names would have put Brentford ties on the National shelf.
(`clubs_from` still matches on names and carries that same weakness —
untouched here, but worth knowing.)

*Correction, made the same evening:* this entry and its commit message named
Werder Bremen as the club sharing BRE with Brentford. Bremen is SVW. The clash
is **Brest**, and the full list is in the entry above.

Eintracht Frankfurt is kept in all three competitions whatever the round, and
takes its own red through a new `tint_backup_teams`: a club whose colour wins
only when none of the league's preferred clubs is in the game. So it is red
against Bayern or Madrid, while a non-rival English opponent still takes the
stripe — and against Arsenal or Chelsea the rival rule has already handed the
colour back to Eintracht, which is the wanted answer by a different route.
Seven pairings checked, including Tottenham (Kyle's own club wins) and a tie
with neither Eintracht nor an English side (still grey).

## 2026-09-07 (later still) — the link moves to the time and network

Tapping a game used to mean tapping the team names. The link is now the whole
right-hand cell — time, network and chips, everything behind the rule — and
the names are plain text again. Hovering underlines the time rather than a
team name.

`.right` became the anchor itself rather than gaining one inside it, so every
rule already written for that cell — the flex column, the rule down its left,
the `solo` centring — keeps working untouched. It only needed `color: inherit`
and `text-decoration: none` to undo being a link.

One real regression came out of this and was caught before it shipped. The
four-column team grid used to live on the anchor *inside* `.teams`, which took
its height from its contents. Moved onto `.teams` itself, it inherited the
cell's stretch to the row's full height, and its two auto tracks stretched
with it: on any row whose right-hand cell is the taller of the two — a row
with chips — the team names sprang **41px apart instead of 3**. `align-content:
start` pins the pair to the top however tall the row grows. Verified by
forcing chips onto every row and re-measuring: 4px with them and without.

The delicate part — the time sitting level with the first team's record and
the network with the second — is unchanged. The same measurement on the live
page carrying the old markup gives identical figures (-2.38px on a two-line
row, 10.13px on a `solo` one), so the move cost nothing there. Checked on the
phone width too: the tap target is 84x47, and the names hold their spacing.

## 2026-09-07 (later) — the red Premier League stripes

Only Arsenal, Liverpool and Manchester United should carry a red stripe. Five
other clubs did: Bournemouth, Brentford, Fulham, Nottingham Forest and
Sunderland. Nobody else — Palace, Everton, Brighton and Ipswich already had
blue overrides, and Hull's orange and Leeds' gold merely look close in a list
of hex values.

Black is what four of them actually own, and black does not work here: against
the row's `#1e1e23` a pure black stripe measures **1.27:1**, which reads as no
stripe at all rather than as black. Newcastle had been sitting like that all
along. So the four go to `#45454e`, a cool charcoal at 1.75:1 — visible, still
reading as black, and deliberately kept clear of the `#9a9a95` that already
means "nothing worth rooting for" (3.36:1 from it, so it cannot be mistaken
for the grey either). Newcastle is included, since it had the same problem.

`#5a5a64` (2.44:1) went out first and read as dark grey rather than black. One
step down the scale is not perceptible — half these shades sit within 1.2:1 of
their neighbour — so it moved three, to 1.39:1 darker than the first attempt
while still holding a 38% wider margin over the row than pure black managed.

Brentford takes the gold of the bee on its crest, `#a87b0a` at 4.35:1. A
brighter gold twins Leeds (`#FFCD00`) or Hull's orange (`#f28800`); this one
keeps 2.54:1 from Leeds and 1.51:1 from Hull, so three warm stripes in one
league stay tellable apart.

Nottingham Forest stays red. Red shirts, white shorts, no third colour: there
is nothing to move it to, and white is not available.

Checked every configured competition for a substring collision before writing
— `Sunderland`, `Fulham`, `Brentford`, `AFC Bournemouth` and `Newcastle
United` each match one club and nothing else. Written to the shared Colors tab
as well as config.json.

## 2026-09-07 — the ESPN links were 404s

Tapping a game opened an ESPN error page. The URL was built from the SPORT
rather than the league — `league["path"].split("/")[0]` — so the NFL and
college football both pointed at `espn.com/football/game/_/gameId/...`, which
does not exist. Soccer was the only sport that worked, and only by accident:
its sport and league segments are the same word, and ESPN redirects the
`/game/` it produced to the `/match/` it wants.

ESPN ships the right URL on the event, under the link whose `rel` includes
`summary`, so it is taken rather than guessed. The constructed form is kept as
a fallback for an event carrying no links, now using the league segment and
saying `/match/` for soccer.

Checked both forms against every competition with a game on the board —
17 leagues, the winter ones on an in-season date — and all 26 URLs returned
200, fallbacks included. The trailing team slug ESPN appends
(`.../401872656/patriots-seahawks`) is decoration: the id alone resolves.

## 2026-09-06 (later) — rivals against each other end grey

Two rivals meeting used to cancel the score colouring outright, so the final
read in the ordinary colour — indistinguishable from a game no rule cared
about. It now goes **grey**, whoever won: a rival won either way, so the
result is the good one and the bad one at once and neither reading is honest.

The pairing is taken from the `skip_when_both` rules already in
`outcome_colours`, so no new team lists: both sides on one rule's own list is
a derby. `rival_derby()` decides it from who is playing, which means the row
can simply carry `data-derby="1"` and the live script needs no score
comparison — it greys at the final whistle and skips the orange rules on the
way, so a derby that somehow also qualified as an upset still ends grey.

Only finals. A derby in progress stays uncoloured exactly as before, and that
already held without help: `upset_side()` refuses these games because Ohio
State, Michigan State and Notre Dame are all on `never_the_underdog`, and
`rival_live_watch()` refuses any game naming two of its own teams. Verified
over both lists in each direction, plus the pairings that are *not* derbies —
Michigan beating Ohio State is still orange, losing to them still grey, and
Tottenham drawing Arsenal still orange.

Arsenal 2–1 Chelsea was on the board the day this went in, and both scores
came out grey.


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

## 2026-09-05 (final pass) — rival wins, live closeness, marquee back to blue

* **A rival winning greys the score**, the mirror of one losing turning it
  orange -- and cancelled when two of them play each other, where the result
  is both at once and so neither. Finals only, like the rest of that group.
* **A live college game shows orange while it is still close**, rather than
  only when the ranked side is behind: within a touchdown in football, two
  possessions in basketball, and nothing at all until the opening period is
  over, where every game is close and none of it means anything yet. The
  numbers live in `upset_watch.live` per league and ride on the row as
  `data-close="7:1"`, so the sport's own thresholds stay in config rather than
  in the browser.
* At **full time** the test goes back to the strict one: the favoured side
  actually lost. A three-point win stops being orange the moment it is over.
* Marquee networks are **blue again**.

## 2026-09-05 (last pass) — Notre Dame, and rivals in trouble while it is on

**Notre Dame joins Ohio State and Michigan State everywhere**: never the
underdog in the upset test, orange when beaten, grey when winning.

**A new live rule, running after the existing ones rather than instead of
them.** The upset test only speaks about ranked sides; this one does not care
about rankings at all, so a rival struggling against nobody in particular
still shows:

* Arsenal or Chelsea level or losing, at any point.
* Ohio State, Michigan State or Notre Dame level or losing in football, once
  the first quarter is over.
* The same three in basketball, once ten minutes of the first half have gone.

That last one needed the **clock**, not just the period: basketball counts
halves, so "ten minutes in" cannot be said in periods. `after_clock` lets a
rule accept its own period once the clock is down to that many seconds, and
`espn.py` now carries `status.clock` for it. Verified at the boundary: 12:00
left in the half stays quiet, 8:00 left lights up.

Two rivals playing each other cancels the rule, as everywhere else.

### The grey was being stripped on load

The build painted Tottenham's 0-0 at Forest grey correctly -- the class was in
the served HTML -- and the live script then removed it. `applyState` toggled
both colour classes from the state it was given, and a state remembered from
before these colours existed carries no `mood` at all, so the toggle cleared
what the build had put there. On a finished game, which is never polled again,
nothing ever put it back.

Two changes: the toggle now only fires when the state has an opinion
(`mood !== undefined`), so a state that predates the feature leaves the
build's own answer alone; and the memory key is versioned, so widening what
gets remembered retires the old entries rather than trying to interpret them.

Reproduced the original failure with a hand-seeded legacy state, then
confirmed the row keeps its grey through it.

### Arsenal and Chelsea wait for the second half

A goalless first half is the ordinary state of a football match and says
nothing yet; by the second it is a result taking shape. Soccer numbers its
halves as periods 1 and 2, so `after_period: 1` is exactly that.

Worth noting for anyone extending this: `after_clock` assumes a clock that
counts DOWN, as the American sports do. Soccer's counts UP -- a finished match
reads 5400 -- so a soccer rule must use `after_period` alone.

### A finished match was still quoting a price

Tottenham's row read "Final" and "+165 ML" together. My own doing: every other
sport goes quiet at the whistle because the SCOREBOARD drops its odds there,
which is the property the rest of the code leans on -- but the soccer rules
read the three-way market from the CORE API instead, and that keeps serving a
price for a match that is over. The bypass took the safeguard with it.

`soccer_line` now declines a finished or called-off game outright, which is
also one fewer request per such row.

## 2026-09-06 — the adaptive icon, and what took it away

Adding a tab favicon on 2026-09-05 pointed `<link rel="icon">` at
`icon-192.png` -- the same file the manifest declares `maskable`. One asset
was then both the plain favicon and the adaptive app icon, and Android stopped
applying the mask.

Checked first that nothing else had moved: the manifest has not changed since
the app was built, and the icon art is safe-zone compliant either way -- the
ring's outer radius is 0.34 of the square, inside the 0.4 a maskable icon
allows, on a ground that fills the corners. So the art was never the problem.

Two changes. The favicon gets **its own file** (`favicon-32.png`, 172 bytes),
so nothing in the HTML names a file the manifest claims. And the manifest now
declares **`any` and `maskable` as separate entries** rather than one
`"any maskable"`: a combined purpose leaves the browser to choose, and one of
the two always ends up wrong. The same file can serve both -- it just has to
say so twice.

## 2026-09-06 — Iowa keeps its black

Iowa's ESPN primary is #231f20, a warm near-black. `invisible_colour()` rejects
it and the alternate stands in, which is why the stripe was gold. Kyle asked
for the black, knowing it reads darker than the rule normally allows — the
Chicago White Sox have been #000000 by override since well before this.

An override wins outright in `_colour()`, ahead of both visibility checks, so
the Sheet row is the whole fix. Written with `set_color.py`, which puts it in
the shared Colors tab AND config.json.

The key is **"Iowa Hawkeyes"**, not "Iowa". Overrides match by substring
(`label.lower() in name`), so "Iowa" would also have repainted Iowa State,
Northern Iowa and Upper Iowa. Checked all four after the write.

## 2026-09-07 — Iowa back to gold, in both apps

Yesterday's black `#231f20` measured **1.02 contrast** against the card. It was
invisible here and on k-money, which is exactly why `invisible_colour()`
rejected it before the override went in. Kyle asked for it back on ESPN's gold
`#fcd116` (11.28) once that was pointed out.

Written with `set_color.py`, so the shared Colors tab and `config.json` both
moved and k-money picks it up on its next build.

Worth remembering how this was framed: the ask was "flip Iowa back to yellow,
to be consistent with Sports Daily". The two were never inconsistent — the
black lived in the tab BOTH read, so both showed black. The real fault was
visibility, not agreement. Check what the pages actually render before
accepting the reason given for a change.
