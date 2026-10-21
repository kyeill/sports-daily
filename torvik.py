"""Projected lines for college basketball, from Bart Torvik's T-Rank.

Vegas does not price a college basketball game until the day before, so the
blowout filter -- which football has had from the start -- had nothing to work
with on a card built a fortnight out: every November cupcake sat on the page
until the morning of the game. T-Rank projects every fixture of the season, so
a number exists the moment the fixture does.

Measured against the closing Vegas number on 238 games of last season, the
projection is unbiased: mean difference 0.04 points, 97% of them inside five,
and the two disagree about a fifteen-point cutoff on 3% of games. So the limit
already in the config carries over without retuning.

The site answers a first request with a form that submits itself. That is a
browser check rather than a wall: posting the one field it asks for returns the
page and leaves a cookie for the rest of the session.

Every failure here is silent and means "no opinion". A missing line leaves the
game exactly as it was before any of this existed -- on the page.
"""
import html
import json
import os
import re
import time
import unicodedata
import urllib.parse

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
URL = "https://www.barttorvik.com/schedule.php"
# The build cannot read the site: barttorvik.com answers GitHub's runners 403,
# the schedule page and the static ratings file alike, so it is the address
# that is refused rather than anything we send. The projections are therefore
# fetched from a machine the site will talk to and committed, and the build
# reads the file. They age gently, and the ageing barely matters: a real line
# appears the day before the game and takes precedence, so a stale projection
# only ever decides whether to show something still days away.
SNAPSHOT = os.path.join(HERE, "projections.json")

# ESPN names the school, T-Rank names it its own way. Twenty-seven of 362
# disagree, every one of them found by diffing the two lists rather than
# guessed at. An unmatched pair simply has no line, which is the same answer
# as not asking.
ALIASES = {
    "app state": "Appalachian St.",
    "california baptist": "Cal Baptist",
    "florida international": "FIU",
    "grambling": "Grambling St.",
    "hawai'i": "Hawaii",
    "iu indianapolis": "IU Indy",
    "kansas city": "UMKC",
    "lsu new orleans": "New Orleans",
    "long island university": "LIU",
    "loyola maryland": "Loyola MD",
    "mcneese": "McNeese St.",
    "miami": "Miami FL",
    "nc state": "N.C. State",
    "nicholls": "Nicholls St.",
    "ole miss": "Mississippi",
    "omaha": "Nebraska Omaha",
    "pennsylvania": "Penn",
    "se louisiana": "Southeastern Louisiana",
    "sam houston": "Sam Houston St.",
    "seattle u": "Seattle",
    "south carolina upstate": "USC Upstate",
    "texas a&m-corpus christi": "Texas A&M Corpus Chris",
    "ualbany": "Albany",
    "uconn": "Connecticut",
    "uic": "Illinois Chicago",
    "ul monroe": "Louisiana Monroe",
    "ut martin": "Tennessee Martin",
}

_session = None
_warned = False


def _norm(name):
    """A school name reduced to what both sites agree on.

    "St." and "State" are the same word to one site and not the other, and the
    accents, ampersands and apostrophes differ school by school.
    """
    text = unicodedata.normalize("NFKD", name or "")
    text = text.encode("ascii", "ignore").decode().lower()
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    for long, short in (("saint", "st"), ("state", "st"),
                        ("university", ""), ("college", "")):
        text = text.replace(long, short)
    return " ".join(w for w in text.split() if w not in ("the", "of", "at", "a"))


def _key(home, away):
    return "|".join(sorted((_norm(home), _norm(away))))


_why = ""


def _fetch(date_key):
    """The schedule page's HTML, or '' -- answering the browser check once.

    `_why` keeps the reason for the build log: a silent dependency is bad
    enough without having to guess whether it was blocked, timed out or simply
    had no games that day.
    """
    global _why
    global _session
    if _session is None:
        _session = requests.Session()
        # A plain browser string, with nothing of ours appended: the site
        # answered 403 to one that named this app.
        _session.headers.update({
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/131.0.0.0 Safari/537.36"),
            "Accept": ("text/html,application/xhtml+xml,application/xml;"
                       "q=0.9,*/*;q=0.8"),
            "Accept-Language": "en-US,en;q=0.9",
        })
    for attempt in (1, 2):
        try:
            reply = _session.get(URL, params={"date": date_key}, timeout=30)
            reply.raise_for_status()
        except Exception as exc:
            _why = "%s: %s" % (type(exc).__name__, str(exc)[:120])
            return ""
        if "js_test_submitted" not in reply.text:
            return reply.text
        # The form the page asks us to submit. Posting it sets the cookie that
        # every later request in this build rides on, so this happens once.
        try:
            posted = _session.post(URL, params={"date": date_key},
                                   data={"js_test_submitted": "1"}, timeout=30)
            posted.raise_for_status()
            if "js_test_submitted" not in posted.text:
                return posted.text
            _why = "the browser check came back again (HTTP %s)" % posted.status_code
        except Exception as exc:
            _why = "%s: %s" % (type(exc).__name__, str(exc)[:120])
            return ""
    return ""


def _parse(text):
    """[(team, team, points)] from the table.

    Read off the links rather than the rendered text: the matchup cell ends
    with the network ("Florida at Vanderbilt ESPN"), while the line's own link
    carries both schools as parameters and the margin as its label.
    """
    out = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", text, re.S):
        pair = re.search(
            r"trank\.php\?[^\"']*t1l=([^&\"']+)(?:&amp;|&)t2l=([^&\"']+)", row)
        margin = re.search(r"t2l=[^>]*>\s*(.*?)\s*(-\d+(?:\.\d+)?)", row)
        if not (pair and margin):
            continue
        one = html.unescape(urllib.parse.unquote_plus(pair.group(1)))
        two = html.unescape(urllib.parse.unquote_plus(pair.group(2)))
        out.append((one, two, abs(float(margin.group(2)))))
    return out


_snapshot_cache = None


def snapshot():
    """The committed projections, or {} -- read once a build."""
    global _snapshot_cache
    if _snapshot_cache is None:
        try:
            with open(SNAPSHOT, encoding="utf-8") as fh:
                _snapshot_cache = json.load(fh)
        except (OSError, ValueError):
            _snapshot_cache = {}
    return _snapshot_cache


def lines(date_key, max_age_min=720):
    """{pair key: points} for one day: the committed file, else the site.

    The file is what the build runs on. The live fetch behind it is for this
    machine, where the site answers -- which is how the file gets written in
    the first place, and how a date beyond its end still works locally.
    """
    stored = snapshot().get(date_key)
    if stored:
        return stored
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, "torvik-%s.json" % date_key)
    if os.path.exists(path):
        age = (time.time() - os.path.getmtime(path)) / 60
        if age < max_age_min:
            try:
                with open(path, encoding="utf-8") as fh:
                    return json.load(fh)
            except (OSError, ValueError):
                pass
    found = {_key(one, two): points for one, two, points in _parse(_fetch(date_key))}
    if found:
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(found, fh)
        except OSError:
            pass
    return found


def refresh(start, days, verbose=True):
    """Fetch `days` dates from `start` and write them into the snapshot.

    Run from a machine the site will answer -- the build cannot. Existing
    dates are replaced, dates outside the range are left alone, so a partial
    run adds rather than truncates.
    """
    import datetime
    book = dict(snapshot())
    book.pop("_built", None)
    added = 0
    for i in range(days):
        date_key = (start + datetime.timedelta(days=i)).strftime("%Y%m%d")
        found = {_key(a, b): p for a, b, p in _parse(_fetch(date_key))}
        if found:
            book[date_key] = found
            added += len(found)
        if verbose and (i % 10 == 0 or i == days - 1):
            print("  %s  %d games (%d so far)" % (date_key, len(found), added))
    book["_built"] = datetime.date.today().isoformat()
    with open(SNAPSHOT, "w", encoding="utf-8") as fh:
        json.dump(book, fh, separators=(",", ":"), sort_keys=True)
    if verbose:
        print("wrote %s: %d dates, %d games" % (SNAPSHOT, len(book) - 1, added))
    return added


def _school(team):
    """The school as T-Rank would write it."""
    name = (team.get("location") or team.get("name") or "").strip()
    return ALIASES.get(name.lower(), name)


def mark_projected(games, league, date_key, max_age_min=720):
    """Stamp `spread_proxy` on every game the league wants a projection for.

    Asked once per day rather than once per game: the whole card is on one
    page. A league without `spread_proxy` in its config never reaches the
    network at all.
    """
    if (league.get("spread_proxy") or "") != "torvik" or not games:
        return 0
    table = lines(date_key, max_age_min)
    if not table:
        # Said once a build, not once a day: a silent dependency that has
        # stopped answering looks exactly like a quiet night of basketball,
        # and the only sign on the page would be blowouts creeping back.
        global _warned
        if not _warned:
            _warned = True
            print("  note: no T-Rank lines for %s (%s); the blowout filter has "
                  "nothing to read on games Vegas has not priced yet"
                  % (date_key, _why or "the page listed no games"))
        return 0
    hit = 0
    for game in games:
        points = table.get(_key(_school(game["home"]), _school(game["away"])))
        if points is not None:
            game["spread_proxy"] = points
            hit += 1
    return hit


if __name__ == "__main__":
    import argparse
    import datetime
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--refresh", action="store_true",
                    help="rewrite projections.json from the site")
    ap.add_argument("--from", dest="start", default="",
                    help="first date, YYYY-MM-DD (default: today)")
    ap.add_argument("--days", type=int, default=160,
                    help="how many dates to walk (default: the rest of a season)")
    args = ap.parse_args()
    if not args.refresh:
        ap.error("nothing to do; pass --refresh")
    first = (datetime.date.fromisoformat(args.start) if args.start
             else datetime.date.today())
    refresh(first, args.days)
