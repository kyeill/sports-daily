"""Render the day's games as a single self-contained HTML page."""

import html
from datetime import datetime

import filters

# Source Sans 3, with the system stack behind it so a cold offline load still
# looks right. Only the two weights the page actually uses are requested.
FONT_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    'family=Source+Sans+3:wght@400;600&display=swap">'
)

CSS = """
/* Dark only, deliberately: the page is read at a glance and should look the
   same on every device, rather than following each one's system setting. */
:root {
  --bg: #16161a; --card: #1e1e23; --ink: #ececea; --muted: #9a9a95;
  --line: #2e2e35; --accent: #e0834f; --pin: #26201c; --pin-line: #4a3628;
  --watch: #1b2029; --watch-line: #33445c; --watch-ink: #8fb0d8; --chip: #2a2a31;
  /* Ranks read better in light blue: a dark navy would vanish against the
     background the same way the black stripe does. */
  --rank: #8fb0d8;
  /* One team line: tall enough for the 20px crest and the name above it.
     The right-hand column uses the same figure, which is the only reason the
     time and the network stay level with the teams they belong to. */
  --line-h: 22px; --line-gap: 3px;
}
html { color-scheme: dark; }
* { box-sizing: border-box; }
body {
  margin: 0; padding: 24px 16px 64px; background: var(--bg); color: var(--ink);
  font: 15px/1.5 "Source Sans 3", -apple-system, "Segoe UI", Roboto, Helvetica,
        Arial, sans-serif;
}
.wrap { max-width: 860px; margin: 0 auto; }
h1 { font-size: 26px; margin: 0 0 2px; letter-spacing: -0.01em; }
.sub { color: var(--muted); font-size: 13px; margin-bottom: 26px; }
.warn {
  background: var(--pin); border: 1px solid var(--pin-line); border-radius: 8px;
  padding: 8px 12px; font-size: 13px; margin-bottom: 18px;
}
.info { color: var(--muted); font-size: 12.5px; margin: -14px 0 20px; }
h2 {
  font-size: 13px; text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--muted); margin: 30px 0 10px; font-weight: 600;
}
.card {
  background: var(--card); border: 1px solid var(--line); border-radius: 10px;
  overflow: hidden;
}
.pinned .card { background: var(--pin); border-color: var(--pin-line); }
.watching .card { background: var(--watch); border-color: var(--watch-line); }
/* One game is two stacked team lines sharing a four-column grid -- crest,
   rank, name, record -- so every field lines up down the page regardless of
   how long the names are. The time and networks sit in a column of their own
   behind a rule. */
.row {
  display: grid; grid-template-columns: 1fr 168px; gap: 14px;
  /* stretch, not center: the right-hand cell has to span the row so its rule
     runs the full height, while the time inside it lines up with the teams. */
  align-items: stretch; padding: 10px 14px;
  border-bottom: 1px solid var(--line); border-left: 3px solid transparent;
}
.row:last-child { border-bottom: none; }
.row.tinted { border-left-color: var(--tint); }
.teams a {
  color: inherit; text-decoration: none; display: grid;
  grid-template-columns: 24px 20px 1fr auto; align-items: center;
  column-gap: 7px; row-gap: var(--line-gap);
  /* minmax, not a fixed height: a name that wraps on a phone still needs the
     room. The competition line below takes its own height. */
  grid-template-rows: minmax(var(--line-h), auto) minmax(var(--line-h), auto);
}
.teams a:hover .t, .teams a:hover .t-short { text-decoration: underline; }
.t-short { display: none; }
.s-logo { display: flex; align-items: center; height: 20px; }
.s-logo img { width: 20px; height: 20px; object-fit: contain; }
.s-rank { color: var(--rank); font-weight: 600; font-size: 11.5px;
  text-align: right; }
/* The line rides inside the name cell rather than in a column of its own: a
   column would align it across both rows, stranding it far from a short name.
   The name is what gives way when space runs out, never the line. */
.s-name { font-size: 14.5px; display: flex; align-items: baseline;
  min-width: 0; }
.s-name .t { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
/* margin rather than a flex gap, because the narrow layout makes this cell a
   block and gaps stop applying there -- which ran the line into the name. */
.s-spread { color: var(--muted); font-size: 12px; flex: 0 0 auto;
  margin-left: 5px; }
.s-rec { color: var(--muted); font-size: 12px; text-align: right;
  white-space: nowrap; }
/* Third row of the same grid, starting at the name column, so it lines up
   with the names above however the columns are sized. */
.s-note { grid-column: 3 / -1; color: var(--muted); font-size: 12px;
  margin-top: 1px; }
/* Time and networks sit against the two team lines, not centred on the row:
   a competition line underneath would otherwise push them out of line with
   the teams they belong to. */
.right {
  border-left: 1px solid var(--line); padding-left: 12px; min-height: 44px;
  display: flex; flex-direction: column; justify-content: flex-start;
  gap: var(--line-gap);
}
/* A time with nothing under it has no second line to pair with, so it centres
   against the pair of team lines instead of sitting on the first. Half of one
   line plus the gap is exactly that offset. */
.right.solo { padding-top: calc((var(--line-h) + var(--line-gap)) / 2); }
/* Each of these is a box the height of a team line with its text centred, so
   line one sits against the first team and line two against the second.

   Equal boxes are not quite enough: what the eye lines up is the baseline,
   and text centred in a box baselines by its own size, so the 13px time sits
   a shade higher than the 14.5px name beside it. Measured with the webfont
   loaded, that residual is about half a pixel -- an earlier reading of 1.9px
   was taken before the font arrived and over-corrected until the time sat
   visibly low. 1px covers the residual plus a little for the smaller, muted
   type, which reads high at matched geometry. Turn this knob if it is still
   not sitting right; it disturbs nothing else. */
.when, .nets { min-height: var(--line-h); display: flex; align-items: center;
  position: relative; top: 1px; }
.when { font-size: 13px; font-variant-numeric: tabular-nums; }
/* Same size and face as the time, differing only in colour, so the two read
   as one block rather than as a label and a badge. */
.nets { font-size: 13px; color: var(--muted); }
.tags { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 2px; }
.chip {
  background: var(--chip); border-radius: 999px; padding: 1px 8px;
  white-space: nowrap;
}
.chip.tv { color: var(--ink); }
.chip.why { background: transparent; border: 1px solid var(--watch-line);
  color: var(--watch-ink); }
.empty { color: var(--muted); padding: 14px; }
@media (max-width: 640px) {
  /* A phone has about 200px for the teams once the right-hand column is paid
     for, so everything gives up a little: the columns, the gaps, the type. */
  /* Measured in the page at mobile sizes: the widest network actually shown
     is "ACC Network" at 68px, against a 49px time -- the long-form names that
     used to be wider are renamed in config (SECN+, CBSSN). 74px of content
     plus the padding and rule is 84px; every pixel saved here goes to the
     names, which is where it is worth something. */
  .row { grid-template-columns: 1fr 84px; gap: 9px; padding: 9px 11px; }
  /* If a network ever comes back longer than the column, clip it rather than
     letting it push the layout around. */
  .nets { overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    display: block; line-height: var(--line-h); }
  .right { padding-left: 9px; }
  .teams a { grid-template-columns: 22px 18px 1fr auto; column-gap: 6px; }
  .s-name { font-size: 14px; }
  /* A long name wraps onto a second line rather than being cut off or
     swapped for an abbreviation. Abbreviating by length was tried and looked
     arbitrary -- it caught "Michigan State" and "Crystal Palace", which read
     perfectly well, so a quarter of the page turned into three-letter codes.
     Only one team in eighty-two is long enough to need two lines. */
  .s-name { display: block; }
  .s-name .t, .s-name .t-short { display: inline; white-space: normal;
    overflow: visible; text-overflow: clip; }
  .s-spread { display: inline; }
  /* Where a short name was offered, it stands in for the full one here. */
  .swap .t { display: none; }
  .swap .t-short { display: inline; }
  .s-rec { font-size: 11.5px; }
  .when, .nets { font-size: 12.5px; }
}
footer { color: var(--muted); font-size: 12px; margin-top: 36px; }
"""


def _esc(text):
    return html.escape(str(text or ""))


def _logo(team, config):
    """ESPN's CDN crest, in whichever variant actually reads on a dark page.

    Normally the `-dark` one, but for some teams that is a flat white
    silhouette. `logos.py` measures the pixels and records those in
    `logo_overrides`, where the default variant reads better. Hot-linked, so
    an onerror swap covers a missing file.
    """
    if not config.get("show_logos", True) or not team.get("logo"):
        return ""
    name = team.get("name") or ""
    src = ((config.get("logo_overrides") or {}).get(name)
           or team.get("logo_dark") or team["logo"])
    swap = "this.onerror=null;this.src=&quot;%s&quot;" % _esc(team["logo"])
    return ('<img src="%s" alt="" loading="lazy" onerror="%s">'
            % (_esc(src), swap))


# Character widths as a fraction of the font size, measured from Source Sans 3
# at weight 400. Grouped by width to stay readable. Summing these reproduces a
# string's real width to within about one percent, and errs wide -- which is
# the safe direction, since the cost of overestimating is a name shortened a
# shade early rather than one that overflows.
_WIDTHS = [
    (0.200, " "), (0.247, "ijíî"), (0.249, "'.:"), (0.255, "l"),
    (0.263, "IÍÎ"), (0.289, "!"), (0.292, "f"), (0.303, "()"),
    (0.311, "-"), (0.338, "t"), (0.347, "r"), (0.350, "/"), (0.419, "s"),
    (0.425, "z"), (0.426, "\""), (0.446, "x"), (0.456, "cç"),
    (0.467, "vy"), (0.476, "Y"), (0.479, "J"), (0.486, "L"), (0.494, "F"),
    (0.495, "k"), (0.496, "eéèê"), (0.497, "0123456789+"),
    (0.504, "agáàâäå"), (0.513, "X"), (0.515, "V"), (0.527, "EÉÈÊ"),
    (0.534, "S"), (0.536, "T"), (0.539, "Z"), (0.542, "oóôöø"),
    (0.543, "AÁÀÂÄÅ"), (0.544, "huúü"), (0.547, "nñ"), (0.553, "b"),
    (0.555, "dpq"), (0.566, "P"), (0.569, "R"), (0.571, "CÇ"),
    (0.579, "K"), (0.588, "B"), (0.609, "&"), (0.615, "D"), (0.617, "G"),
    (0.645, "UÚÜ"), (0.647, "NÑ"), (0.652, "H"), (0.664, "OQÓÔÖØ"),
    (0.719, "w"), (0.727, "M"), (0.786, "W"), (0.829, "m")
]
CHAR_W = {ch: w for w, chars in _WIDTHS for ch in chars}

# What a phone leaves for a name, in pixels. At a 375px viewport: 343 after the
# body padding, 341 after the card border, 338 after the tint stripe, 316 after
# the row padding; the right-hand column and its gap take 93, leaving 223 for
# the teams; the crest, rank and their gaps take 58 and the record 22.
NAME_BUDGET = 143
LINE_MARGIN = 5      # the gap between a name and its betting line
NAME_PX = 14         # both as the narrow stylesheet renders them
LINE_PX = 12


def _text_width(text, size):
    """Roughly what `text` will measure at `size`, in pixels."""
    return sum(CHAR_W.get(ch, 0.55) for ch in text) * size


def _side_html(team, show_records, config, line=""):
    """One team as four grid cells: crest, rank, name, record.

    Four cells rather than one run of text, because both teams share the grid:
    that is what makes the names start at the same place whether or not a team
    is ranked, and the records finish at the same place whatever the names do.
    """
    rank = ('%d' % team["rank"]) if team.get("rank") else ""
    detail = team.get("detail") if show_records else ""
    spread = ('<span class="s-spread">(%s)</span>' % _esc(line)) if line else ""
    label = team.get("label") or team.get("short") or team.get("name") or ""

    # Past what a phone fits, ESPN's short name is offered alongside and the
    # narrow stylesheet picks it: "Manchester United" becomes "Man United",
    # "Brighton & Hove Albion" becomes "Brighton". The test is the name's
    # measured width, not its length -- counting characters shortened
    # "Crystal Palace", which is narrow enough to fit even beside a moneyline,
    # while letting wider names of the same length through.
    short = team.get("short") or ""
    cell, alt = "s-name", ""
    needed = _text_width(label, NAME_PX)
    if line:
        needed += LINE_MARGIN + _text_width("(%s)" % line, LINE_PX)
    if needed > NAME_BUDGET and short and len(short) < len(label):
        alt = '<span class="t-short">%s</span>' % _esc(short)
        cell = "s-name swap"     # marks the pair, so no :has() is needed
    return (
        '<span class="s-logo">%s</span>'
        '<span class="s-rank">%s</span>'
        '<span class="%s"><span class="t">%s</span>%s%s</span>'
        '<span class="s-rec">%s</span>'
    ) % (_logo(team, config), rank, cell, _esc(label), alt, spread, _esc(detail))


def _when(game):
    if game["state"] == "in":
        return game.get("status_detail") or "live"
    if game["state"] == "post":
        score = "%s-%s" % (game["away"].get("score"), game["home"].get("score"))
        return "final" if "None" in score else "final %s" % score
    # %-I is not portable on Windows; strip the leading zero by hand.
    return game["start_local"].strftime("%I:%M %p").lstrip("0")


def _game_html(game, show_league, config):
    show_records = config.get("show_records", True)
    # Soccer is written home side first; every other sport is away at home.
    # With the teams stacked, that order is what says which is which -- there
    # is no "at" between them any more.
    if (game.get("sport") or "") == "Soccer":
        first, second, order = game["home"], game["away"], ("home", "away")
    else:
        first, second, order = game["away"], game["home"], ("away", "home")

    # The line belongs against the team it is about: a point spread where the
    # sport has one, otherwise the moneyline, which espn.py labels ML.
    lines = {"home": "", "away": ""}
    if config.get("show_odds", True) and game.get("spread_side"):
        lines[game["spread_side"]] = game.get("spread_label") or ""

    detail = filters.detail_of(game, config, game.get("_league"))
    # Which competition, for a club that plays in several -- on the detail line
    # rather than as a right-hand badge: "Carabao Cup Second Round".
    if show_league and (game.get("sport") or "") == "Soccer":
        label = game["league_label"]
        # "MLS MLS Cup" reads badly; the round already names it.
        if not detail.startswith(label):
            detail = ("%s %s" % (label, detail)).strip()
    # Stacking drops the "at"/"vs", and with it the only sign of a neutral
    # site. Bowls and tournament rounds already say so by name, so this only
    # speaks up when nothing else would.
    if game.get("neutral") and not detail:
        detail = "Neutral site"
    note = ('<span class="s-note">%s</span>' % _esc(detail)) if detail else ""

    networks = "/".join(filters.display_networks(game, config))
    tags = "".join('<span class="chip why">%s</span>' % _esc(t)
                   for t in game.get("tags") or [])
    tags = ('<div class="tags">%s</div>' % tags) if tags else ""

    # Your team's colour when you are involved, otherwise whichever team makes
    # the game interesting; black when both sides do.
    tint = (game.get("tint") or "").strip()
    attrs = (' class="row tinted" style="--tint:#%s"' % _esc(tint))         if tint and config.get("show_colors", True) else ' class="row"'

    # An empty network line would still occupy a team line's worth of height,
    # so it is left out entirely -- and when nothing else is there, the time
    # centres rather than sitting against the first team.
    nets = ('<div class="nets">%s</div>' % _esc(networks)) if networks else ""
    solo = " solo" if not networks and not tags else ""

    return (
        '<div%s>'
        '<div class="teams"><a href="%s">%s%s%s</a></div>'
        '<div class="right%s"><div class="when">%s</div>%s%s</div>'
        '</div>'
    ) % (attrs, _esc(game["link"]),
         _side_html(first, show_records, config, lines[order[0]]),
         _side_html(second, show_records, config, lines[order[1]]),
         note, solo, _esc(_when(game)), nets, tags)


def _section(title, games, show_league, config):
    if not games:
        return ""
    rows = "".join(_game_html(g, show_league, config) for g in games)
    return '<h2>%s</h2><div class="card">%s</div>' % (_esc(title), rows)


def sections_for(games, config):
    """[(heading, games)] for everything outside the pinned blocks.

    Shared by the page and the console output so the two cannot drift -- they
    already had, with the console missing the ranked split entirely.
    """
    rank = {lg["label"]: lg.get("sort_rank", 99) for lg in config.get("leagues", [])}
    split = {lg["label"] for lg in config.get("leagues", []) if lg.get("split_ranked")}
    by_league = {}
    for game in games:
        label = game["league_label"]
        if label in split:
            # A top-25 game is a different proposition from the rest of a
            # college slate, so it gets its own heading.
            ranked = any(t.get("rank") for t in (game["home"], game["away"]))
            label = ("Ranked %s" % label) if ranked else label
            # Ranked leads when both start at the same minute.
            rank[label] = rank.get(game["league_label"], 99) + (0 if ranked else 0.5)
        by_league.setdefault(label, []).append(game)
    # Sports come in the order their first game starts; the configured rank
    # only breaks ties between sports starting at the same minute.
    order = sorted(by_league,
                   key=lambda label: (min(g["start_local"] for g in by_league[label]),
                                      rank.get(label, 99), label))
    return [(label, by_league[label]) for label in order]


def day_body(day, games, config, notes=None, info=None):
    """The sections for one day, without the page chrome.

    Shared by the single-day page and the multi-day app so there is exactly one
    renderer; the app only adds a day picker around this.
    """
    return _body(games, config, notes, info)


def summary(games):
    """'12 games - 3 for your teams - 2 other highlights'."""
    pinned = [g for g in games if g.get("tier") == "favorite"]
    watching = [g for g in games if g.get("tier") == "watch"]
    counts = "%d game%s" % (len(games), "" if len(games) == 1 else "s")
    if pinned:
        counts += " &middot; %d for my teams" % len(pinned)
    if watching:
        counts += " &middot; %d highlighted" % len(watching)
    return counts


def _body(games, config, notes=None, info=None):
    games = sorted(games, key=lambda g: (g["start_local"], g["league_label"]))
    pinned = [g for g in games if g.get("tier") == "favorite"]
    # Rivals get their own block under My Teams -- but a rival playing one of
    # your teams is already up there, so it is not repeated.
    rivals = [g for g in games if g.get("tier") != "favorite" and g.get("highlight")]
    rest = [g for g in games if g.get("tier") != "favorite" and not g.get("highlight")]

    parts = []
    for note in notes or []:
        parts.append('<div class="warn">%s</div>' % _esc(note))
    for line in info or []:
        parts.append('<div class="info">%s</div>' % _esc(line))
    if pinned:
        parts.append('<div class="pinned">%s</div>' %
                     _section("Main Slate", pinned, True, config))
    if rivals:
        parts.append('<div class="watching">%s</div>' %
                     _section("Highlights", rivals, True, config))

    # Everything else sits in its own sport, highlights included -- the tag on
    # the row already says why it is there, so a separate section was just an
    # extra heading to scroll past.
    for label, block in sections_for(rest, config):
        parts.append(_section(label, block, False, config))

    if not games:
        parts.append('<div class="card"><div class="empty">'
                     'No games match your filters today.</div></div>')
    return "".join(parts)


def render(day, games, config, generated=None, notes=None, info=None):
    """A standalone single-day page."""
    body = _body(games, config, notes, info)
    games = sorted(games, key=lambda g: (g["start_local"], g["league_label"]))
    pinned = [g for g in games if g.get("tier") == "favorite"]
    watching = [g for g in games if g.get("tier") == "watch"]

    generated = generated or datetime.now()
    counts = summary(games)

    return (
        '<title>Games &middot; %s</title>' + FONT_LINK + '\n<style>%s</style>\n'
        '<div class="wrap"><h1>%s</h1>%s'
        '<footer>Generated %s from ESPN. Times shown in %s.</footer></div>'
    ) % (
        _esc(day.strftime("%b %d").replace(" 0", " ")),
        CSS,
        _esc(day.strftime("%A, %B %d").replace(" 0", " ")),
        body,
        _esc(generated.strftime("%b %d, %I:%M %p").replace(" 0", " ")),
        _esc(config.get("timezone", "local")),
    )
