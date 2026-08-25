"""Render one real game from every competition and round onto a single page.

    python showcase.py    -> output/showcase.html

No single real date contains an FA Cup final, a World Series game, the Frozen
Four and a Sweet 16 tie, so this pulls a genuine example of each from its own
date and lays them out together. It is a review tool: it shows exactly how each
scenario renders -- rounds, series lines, aggregates, tints, tags, networks --
without waiting a year for them all to come round.
"""

import os
from datetime import date
from zoneinfo import ZoneInfo

import espn
import filters
import race
import render
import sheets
import sports_daily

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output", "showcase.html")

# (heading, league key, date, substring to pick a specific game or "")
SCENARIOS = [
    ("NFL - standalone Sunday night", "nfl", "20251214", ""),
    ("NFL - Thanksgiving", "nfl", "20251127", "GB"),
    ("NFL - wild card round", "nfl", "20260111", ""),
    ("MLB - my team, regular season", "mlb", "20260824", "DET"),
    ("MLB - wild card round", "mlb", "20251001", ""),
    ("MLB - World Series, with series score", "mlb", "20251027", ""),
    ("NBA - my team, regular season", "nba", "20260117", "DET"),
    ("NBA - conference finals", "nba", "20260525", ""),
    ("NHL - first round", "nhl", "20260422", ""),
    ("NHL - Stanley Cup Final", "nhl", "20260609", ""),
    ("College football - ranked", "college-football", "20251018", "LSU"),
    ("College football - my team vs a rival", "college-football", "20251129", "OSU"),
    ("College football - rival elsewhere", "college-football", "20251018", "ND"),
    ("College football - neutral site", "college-football", "20260905", "BAY"),
    ("College football - bowl game", "college-football", "20251227", ""),
    ("College basketball - regular season", "mens-college-basketball", "20260117", "MICH"),
    ("College basketball - conference tournament", "mens-college-basketball", "20260313", "MICH"),
    ("March Madness - first round", "mens-college-basketball", "20260319", "MICH"),
    ("March Madness - Sweet 16", "mens-college-basketball", "20260326", ""),
    ("March Madness - national championship", "mens-college-basketball", "20260406", ""),
    ("College hockey - my team", "mens-college-hockey", "20260214", "MICH"),
    ("College hockey - conference tournament", "mens-college-hockey", "20260320", ""),
    ("College hockey - Frozen Four", "mens-college-hockey", "20260409", ""),
    ("Premier League - weekend", "epl", "20260829", "TOT"),
    ("Premier League - midweek", "epl", "20251203", "ARS"),
    ("FA Cup - final", "facup", "20260516", ""),
    ("Carabao Cup - second round", "eflcup", "20260826", "TOT"),
    ("Champions League - league phase", "ucl", "20260128", "TOT"),
    ("Champions League - round of 16, 2nd leg", "ucl", "20260317", "ARS"),
    ("Europa League - knockout", "uel", "20260312", ""),
    ("MLS - regular season", "mls", "20260829", "ATL"),
    ("MLS - playoffs", "mls", "20251101", ""),
    ("MLS - MLS Cup", "mls", "20251206", ""),
    ("Leagues Cup - knockout", "leaguescup", "20250820", ""),
    ("Gold Cup - USMNT", "goldcup", "20250706", ""),
    ("Nations League - USMNT", "nations", "20250320", ""),
]


def pick(config, tz, key, day, want):
    league = next((l for l in config["leagues"] if l["key"] == key), None)
    if not league:
        return None, "no such league: %s" % key
    games = espn.games_for(league, day, tz, cache_minutes=99999)
    if not games:
        return None, "no games found on %s" % day
    sports_daily.mark_standalone(games)
    chosen = None
    for game in games:
        keep, _, _ = filters.evaluate(game, league, config)
        sides = (game["away"]["abbr"], game["home"]["abbr"])
        if want and want not in sides:
            continue
        if keep and chosen is None:
            chosen = game
        if want and keep:
            chosen = game
            break
    if chosen is None:
        # Fall back to any game, so a scenario still shows what it looks like.
        chosen = games[0]
        filters.evaluate(chosen, league, config)
        return chosen, "not kept by the filters; shown anyway"
    return chosen, ""


def main():
    config = sports_daily.load_config()
    sheets.load(config)
    tz = ZoneInfo(config.get("timezone", "America/New_York"))
    # Put the NFL race in season so the chase tags appear on the examples.
    race.merge_into(config, today=date(2025, 12, 14))

    parts = []
    for title, key, day, want in SCENARIOS:
        game, note = pick(config, tz, key, day, want)
        stamp = "%s-%s-%s" % (day[:4], day[4:6], day[6:])
        # Plain text only: _section escapes its title, as it should, so any
        # markup passed in here renders as literal tags.
        heading = "%s · %s%s" % (title, stamp,
                                      (" · " + note) if note else "")
        if not game:
            parts.append('<h2>%s</h2><div class="card"><div class="empty">'
                         'nothing to show</div></div>' % heading)
            continue
        parts.append(render._section(heading, [game], True, config))
        print("  %-46s %s" % (title, note or "ok"))

    page = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Showcase</title><style>%s</style></head><body><div class="wrap">'
        '<h1>Every competition, one page</h1>'
        '<div class="info">One real game from each competition and round, each '
        'from its own date, rendered exactly as it would appear on the day.'
        '</div>%s</div></body></html>'
    ) % (render.CSS, "".join(parts))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(page)
    print("wrote %s" % OUT)


if __name__ == "__main__":
    main()
