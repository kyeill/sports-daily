"""Render the day's games as a single self-contained HTML page."""

import html
from datetime import datetime

import filters

CSS = """
/* Dark only, deliberately: the page is read at a glance and should look the
   same on every device, rather than following each one's system setting. */
:root {
  --bg: #16161a; --card: #1e1e23; --ink: #ececea; --muted: #9a9a95;
  --line: #2e2e35; --accent: #e0834f; --pin: #26201c; --pin-line: #4a3628;
  --watch: #1b2029; --watch-line: #33445c; --watch-ink: #8fb0d8; --chip: #2a2a31;
}
html { color-scheme: dark; }
* { box-sizing: border-box; }
body {
  margin: 0; padding: 24px 16px 64px; background: var(--bg); color: var(--ink);
  font: 15px/1.5 -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
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
.game {
  display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap;
  padding: 11px 14px; border-bottom: 1px solid var(--line);
}
.game:last-child { border-bottom: none; }
.time {
  flex: 0 0 78px; font-variant-numeric: tabular-nums; color: var(--muted);
  font-size: 13px;
}
.match { flex: 1 1 300px; min-width: 0; display: flex; align-items: center;
  gap: 6px; flex-wrap: wrap; }
/* These sit inside an <a>, so they are inline-level boxes and align on their
   BASELINES by default -- and an inline-flex box holding a 20px logo has a
   very different baseline from 12px text, which dropped "at" below the names.
   vertical-align: middle aligns them on their centres instead. */
.side { display: inline-flex; align-items: center; gap: 5px; min-height: 20px;
  vertical-align: middle; }
.side img { width: 20px; height: 20px; object-fit: contain; flex: 0 0 20px; }
.at { display: inline-block; vertical-align: middle;
  color: var(--muted); font-size: 12px; }
.game { border-left: 3px solid transparent; }
.game.tinted { border-left-color: var(--tint); }
.match a { color: inherit; text-decoration: none; }
.match a:hover { text-decoration: underline; }
.rank { color: var(--accent); font-weight: 600; font-size: 12px; }
.rec { color: var(--muted); font-size: 12px; }
.meta {
  flex: 1 1 220px; display: flex; gap: 6px; flex-wrap: wrap;
  justify-content: flex-end; font-size: 12px; color: var(--muted);
}
.chip {
  background: var(--chip); border-radius: 999px; padding: 1px 8px;
  white-space: nowrap;
}
.chip.tv { color: var(--ink); }
.chip.why { background: transparent; border: 1px solid var(--watch-line);
  color: var(--watch-ink); }
.lg { font-size: 11px; letter-spacing: 0.04em; text-transform: uppercase; }
.note { color: var(--accent); font-size: 12px; }
.empty { color: var(--muted); padding: 14px; }
footer { color: var(--muted); font-size: 12px; margin-top: 36px; }
"""


def _esc(text):
    return html.escape(str(text or ""))


def _logo(team, config):
    """ESPN's CDN logo. Hot-linked, so it needs a connection to display."""
    if not config.get("show_logos", True) or not team.get("logo"):
        return ""
    return '<img src="%s" alt="" loading="lazy">' % _esc(team["logo"])


def _team_html(team, show_records, config):
    bits = [_logo(team, config)]
    if team.get("rank"):
        bits.append('<span class="rank">#%d</span>' % team["rank"])
    bits.append(_esc(team.get("label") or team.get("short") or team.get("name")))
    detail = team.get("detail") if show_records else ""
    if detail:
        bits.append('<span class="rec">(%s)</span>' % _esc(detail))
    return '<span class="side">%s</span>' % " ".join(b for b in bits if b)


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
    if (game.get("sport") or "") == "Soccer":
        first, second, joiner = game["home"], game["away"], "vs"
    else:
        first, second, joiner = game["away"], game["home"], "at"
    if game.get("neutral"):
        joiner = "vs"          # nobody is "at" a neutral site
    matchup = "%s <span class=\"at\">%s</span> %s" % (
        _team_html(first, show_records, config), joiner,
        _team_html(second, show_records, config))

    meta = []
    # In My Teams the sport is obvious from the team -- except in soccer, where
    # Tottenham and Atlanta United turn up in half a dozen competitions.
    if show_league and (game.get("sport") or "") == "Soccer":
        meta.append('<span class="chip lg">%s</span>' % _esc(game["league_label"]))
    for tag in game.get("tags") or []:
        meta.append('<span class="chip why">%s</span>' % _esc(tag))
    for name in filters.display_networks(game, config):
        meta.append('<span class="chip tv">%s</span>' % _esc(name))
    if config.get("show_odds", True) and game.get("spread"):
        meta.append('<span class="chip">%s</span>' % _esc(game["spread"]))

    # "2 GB", "Game 3", "LAD lead series 2-1", "advance 3-1 on aggregate"
    detail = filters.detail_of(game)
    note = ('<div class="note">%s</div>' % _esc(detail)) if detail else ""

    # Your team's colour when you are involved, otherwise whichever team makes
    # the game interesting; black when both sides do.
    tint = (game.get("tint") or "").strip()
    attrs = (' class="game tinted" style="--tint:#%s"' % _esc(tint)) \
        if tint and config.get("show_colors", True) else ' class="game"'

    return (
        '<div%s>'
        '<div class="time">%s</div>'
        '<div class="match"><a href="%s">%s</a>%s</div>'
        '<div class="meta">%s</div>'
        '</div>'
    ) % (attrs, _esc(_when(game)), _esc(game["link"]), matchup, note, "".join(meta))


def _section(title, games, show_league, config):
    if not games:
        return ""
    rows = "".join(_game_html(g, show_league, config) for g in games)
    return '<h2>%s</h2><div class="card">%s</div>' % (_esc(title), rows)


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
    rivals = [g for g in games if g.get("tier") != "favorite" and g.get("rival")]
    rest = [g for g in games if g.get("tier") != "favorite" and not g.get("rival")]

    parts = []
    for note in notes or []:
        parts.append('<div class="warn">%s</div>' % _esc(note))
    for line in info or []:
        parts.append('<div class="info">%s</div>' % _esc(line))
    if pinned:
        parts.append('<div class="pinned">%s</div>' %
                     _section("My Teams", pinned, True, config))
    if rivals:
        parts.append('<div class="watching">%s</div>' %
                     _section("Rivals", rivals, True, config))

    # Everything else sits in its own sport, highlights included -- the tag on
    # the row already says why it is there, so a separate section was just an
    # extra heading to scroll past.
    rank = {lg["label"]: lg.get("sort_rank", 99) for lg in config.get("leagues", [])}
    split = {lg["label"] for lg in config.get("leagues", []) if lg.get("split_ranked")}
    by_league = {}
    for game in rest:
        label = game["league_label"]
        if label in split:
            # Ranked games are a different proposition from the rest of a
            # college slate, so they get their own heading.
            ranked = any(t.get("rank") for t in (game["home"], game["away"]))
            label = "%s %s %s" % (label, "–", "Ranked" if ranked else "Other")
            # Ranked leads on a tie, so nudge it ahead of Other in the rank.
            rank[label] = rank.get(game["league_label"], 99) + (0 if ranked else 0.5)
        by_league.setdefault(label, []).append(game)
    # Sports come in the order their first game starts; the configured rank
    # only breaks ties between sports starting at the same minute.
    order = sorted(by_league,
                   key=lambda label: (min(g["start_local"] for g in by_league[label]),
                                      rank.get(label, 99), label))
    for label in order:
        parts.append(_section(label, by_league[label], False, config))

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
        '<title>Games &middot; %s</title>\n<style>%s</style>\n'
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
