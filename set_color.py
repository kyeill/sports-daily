"""Set a team's stripe colour in the shared Colors tab, and in config.json.

    python set_color.py "Everton" 003399
    python set_color.py "Everton" 003399 --check   # say what would happen

The Sheet is the MASTER list -- sports-daily, standings and k-money all read
it, and it is merged OVER config.json at build time. config.json is the
committed fallback, so both are written: the Sheet so the change is shared and
takes effect at the next build, config.json so a Sheet outage cannot lose it.

Writing needs the Apps Script endpoint, because Google's CSV endpoint only
reads. Put its URL and token in secrets.json (gitignored):

    {"colors_endpoint": "https://script.google.com/macros/s/AKfy.../exec",
     "colors_token": "the string you passed to setColorToken()"}

Without that file nothing is lost: the colour still goes into config.json and
the row to paste into the Sheet is printed.
"""

import argparse
import collections
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "config.json")
SECRETS = os.path.join(HERE, "secrets.json")


def _hex(value):
    """'#0A2240' -> '0a2240', or None if it is not a colour."""
    clean = (value or "").strip().lstrip("#").lower()
    if len(clean) == 6 and all(c in "0123456789abcdef" for c in clean):
        return clean
    return None


def _load(path):
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh, object_pairs_hook=collections.OrderedDict)


def write_config(team, colour):
    """Put the colour in config.json, which is the committed fallback."""
    config = _load(CONFIG)
    colours = config.setdefault("team_colors", collections.OrderedDict())
    before = colours.get(team)
    colours[team] = colour
    config["team_colors"] = collections.OrderedDict(sorted(colours.items()))
    with io.open(CONFIG, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(config, indent=2, ensure_ascii=False) + "\n")
    return before


def write_sheet(team, colour):
    """-> (ok, message). Never raises: a failed write must not lose the colour."""
    if not os.path.exists(SECRETS):
        return False, "no secrets.json; the Sheet was not touched"
    try:
        secrets = _load(SECRETS)
        url = (secrets.get("colors_endpoint") or "").strip()
        token = (secrets.get("colors_token") or "").strip()
    except Exception as exc:
        return False, "secrets.json unreadable (%s)" % exc
    if not url or not token:
        return False, "secrets.json has no colors_endpoint/colors_token"

    import requests
    try:
        # The web app answers on GET and redirects to a googleusercontent URL,
        # which requests follows for us.
        reply = requests.get(url, timeout=30, params={
            "action": "color", "token": token, "team": team, "color": colour})
        reply.raise_for_status()
        body = reply.json()
    except Exception as exc:
        return False, "endpoint call failed (%s)" % exc
    if not body.get("ok"):
        return False, "endpoint refused it: %s" % (body.get("error") or body)
    return True, "sheet row %s" % body.get("action", "written")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("team", help="the ESPN name, or any part of it that is unique")
    ap.add_argument("color", help="6-digit hex, with or without the #")
    ap.add_argument("--check", action="store_true",
                    help="say what would happen and change nothing")
    args = ap.parse_args(argv)

    colour = _hex(args.color)
    if not colour:
        print("%r is not a 6-digit hex colour" % args.color)
        return 2
    team = args.team.strip()
    if not team:
        print("no team given")
        return 2

    if args.check:
        current = (_load(CONFIG).get("team_colors") or {}).get(team)
        print("%s: %s -> %s" % (team, current or "(unset)", colour))
        print("secrets.json present: %s" % os.path.exists(SECRETS))
        return 0

    before = write_config(team, colour)
    print("config.json: %s %s -> %s"
          % (team, before or "(unset)", colour))
    ok, note = write_sheet(team, colour)
    print("sheet: %s" % note)
    if not ok:
        # The Sheet wins at build time, so a row that is missing there is not
        # merely untidy: an older value already in it would keep overriding
        # what was just written here.
        print("\nPaste this into the Colors tab so the shared list agrees:")
        print("    %s\t%s" % (team, colour))
    return 0


if __name__ == "__main__":
    sys.exit(main())
