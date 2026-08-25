"""Side-by-side options for the detail-line colour and the page font.

    python styles.py    -> output/style-options.html

Renders the same handful of real rows once per option, so the choice is made
by looking rather than by imagining. Fonts are all locally installed on
Windows and macOS, so nothing is fetched.
"""

import os
from zoneinfo import ZoneInfo

import espn
import filters
import render
import sheets
import sports_daily

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output", "style-options.html")

# A spread of rows: a plain game, a series, a European tie, a chase.
SAMPLES = [
    ("mlb", "20251027", ""),
    ("nhl", "20260609", ""),
    ("ucl", "20260317", "ARS"),
    ("eflcup", "20260826", "TOT"),
    ("college-football", "20251129", "OSU"),
    ("mls", "20251206", ""),
]

COLOURS = [
    ("Current - accent orange", "#e0834f"),
    ("Light grey", "#b9b9b4"),
    ("Muted grey (same as times)", "#9a9a95"),
    ("Dim grey", "#7e7e79"),
    ("Near-white", "#d8d8d4"),
    ("Cool blue-grey", "#8fb0d8"),
]

# Web fonts worth considering for a dense, data-heavy page. Each is a variable
# font with real numeral support; Inter and IBM Plex offer tabular figures,
# which keeps kickoff times from shifting column to column.
GOOGLE_FONTS = [
    ("Inter - the modern UI default", "Inter", "'Inter', sans-serif"),
    ("Source Sans 3 - warmer, narrower", "Source+Sans+3", "'Source Sans 3', sans-serif"),
    ("IBM Plex Sans - engineered, tabular", "IBM+Plex+Sans", "'IBM Plex Sans', sans-serif"),
    ("Public Sans - plain, very legible", "Public+Sans", "'Public Sans', sans-serif"),
    ("Manrope - rounder, friendlier", "Manrope", "'Manrope', sans-serif"),
    ("Figtree - geometric", "Figtree", "'Figtree', sans-serif"),
    ("Barlow - slightly condensed, fits more", "Barlow", "'Barlow', sans-serif"),
]

FONTS = [
    ("Current - system UI",
     '-apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif'),
    ("Segoe UI Variable", '"Segoe UI Variable Text", "Segoe UI", sans-serif'),
    ("Verdana - wide, very legible", 'Verdana, Geneva, sans-serif'),
    ("Trebuchet MS - humanist", '"Trebuchet MS", "Segoe UI", sans-serif'),
    ("Georgia - serif", 'Georgia, "Times New Roman", serif'),
    ("Consolas - monospace", 'Consolas, "Courier New", monospace'),
]


def rows(config, tz):
    out = []
    for key, day, want in SAMPLES:
        league = next(l for l in config["leagues"] if l["key"] == key)
        for game in espn.games_for(league, day, tz, cache_minutes=99999):
            if want and want not in (game["away"]["abbr"], game["home"]["abbr"]):
                continue
            filters.evaluate(game, league, config)
            out.append(render._game_html(game, True, config))
            break
    return "".join(out)


def google_page(body):
    families = "&".join("family=%s:wght@400;600" % g[1] for g in GOOGLE_FONTS)
    link = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?%s'
            '&display=swap">' % families)
    blocks = ["<h1>Google Fonts</h1>",
              '<div class="info">These are fetched over the network on first '
              'load, then cached by the service worker. Everything else on the '
              'page works offline either way.</div>']
    for label, _, stack in GOOGLE_FONTS:
        blocks.append('<h2>%s</h2><div class="card" style="font-family:%s">%s</div>'
                      % (label, stack, body))
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Google Fonts</title>%s<style>%s'
        ' h1 { font-size: 20px; margin: 32px 0 6px; }'
        '</style></head><body><div class="wrap">%s</div></body></html>'
    ) % (link, render.CSS, "".join(blocks))


def main():
    config = sports_daily.load_config()
    sheets.load(config)
    tz = ZoneInfo(config.get("timezone", "America/New_York"))
    body = rows(config, tz)

    blocks = ["<h1>Detail line colour</h1>"]
    for label, colour in COLOURS:
        blocks.append(
            '<h2>%s &nbsp;<span style="text-transform:none;letter-spacing:0;'
            'font-weight:400">%s</span></h2>'
            '<div class="card" style="--note:%s">%s</div>'
            % (label, colour, colour, body))

    blocks.append('<h1 style="margin-top:44px">Font</h1>')
    for label, stack in FONTS:
        blocks.append(
            '<h2>%s</h2><div class="card" style="font-family:%s">%s</div>'
            % (label, stack.replace('"', "'"), body))

    page = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Style options</title><style>%s'
        # Each card overrides the detail colour through a CSS variable.
        '\n.card .note { color: var(--note, var(--accent)); }'
        '\nh1 { font-size: 20px; margin: 32px 0 6px; }'
        '</style></head><body><div class="wrap">%s</div></body></html>'
    ) % (render.CSS, "".join(blocks))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(page)
    print("wrote %s" % OUT)

    google = os.path.join(os.path.dirname(OUT), "font-options.html")
    with open(google, "w", encoding="utf-8") as fh:
        fh.write(google_page(body))
    print("wrote %s" % google)


if __name__ == "__main__":
    main()
