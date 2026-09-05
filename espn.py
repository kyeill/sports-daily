"""Fetch and normalize ESPN's public scoreboard API into plain dicts.

One request per configured league per day. Responses are cached on disk so
repeated runs (and re-renders) do not re-hit the API.

Verified payload shapes on 2026-08-24 -- see README for the trap list.
"""

import json
import os
import re
import time
from datetime import datetime, timezone

import requests

SITE = "https://site.api.espn.com/apis/site/v2/sports"
CORE = "https://sports.core.api.espn.com/v2/sports"
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
# ESPN 403s browser-style User-Agent strings from a non-browser client but
# serves the requests default (python-requests/x.y) fine. Do NOT set one.
UA = {"Accept": "application/json"}

UNRANKED = 99  # ESPN uses curatedRank.current == 99 for "not ranked"

# Fetches that failed this run, so the page can say so rather than looking
# like a quiet day.
FAILURES = []


def _cache_path(name):
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)
    return os.path.join(CACHE, safe + ".json")


def _get(url, params=None, cache_key=None, max_age_min=30):
    """GET with a disk cache. Returns parsed JSON, or None on failure."""
    os.makedirs(CACHE, exist_ok=True)
    path = _cache_path(cache_key) if cache_key else None
    if path and os.path.exists(path):
        age_min = (time.time() - os.path.getmtime(path)) / 60
        if age_min < max_age_min:
            try:
                with open(path, encoding="utf-8") as fh:
                    return json.load(fh)
            except (OSError, ValueError):
                pass  # corrupt cache: fall through and refetch
    try:
        resp = requests.get(url, params=params, headers=UA, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # network, HTTP, or JSON -- all non-fatal
        print("  ! fetch failed: %s (%s)" % (url, exc))
        if path and os.path.exists(path):
            print("    using stale cache")
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        label = (cache_key or url).split("-")[0]
        if label not in FAILURES:
            FAILURES.append(label)
        return None
    if path:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
    return data


# --- conference names -------------------------------------------------------
# The scoreboard carries team.conferenceId but not its name. The core API's
# group children resolve id -> name; cached for a month since it barely moves.

_CONF_ROOT = {
    "basketball/mens-college-basketball": ("basketball", "mens-college-basketball", "50"),
    "football/college-football": ("football", "college-football", "80"),
    "hockey/mens-college-hockey": ("hockey", "mens-college-hockey", "50"),
}
_conf_cache = {}


def conference_names(league_path, season=None):
    """{conferenceId: name} for a college league; {} if unavailable."""
    if league_path in _conf_cache:
        return _conf_cache[league_path]
    spec = _CONF_ROOT.get(league_path)
    if not spec:
        _conf_cache[league_path] = {}
        return {}
    sport, league, root = spec
    season = season or datetime.now().year
    url = "%s/%s/leagues/%s/seasons/%s/types/2/groups/%s/children" % (
        CORE, sport, league, season, root)
    data = _get(url, {"limit": 200},
                cache_key="conf-%s-%s" % (league, season),
                max_age_min=60 * 24 * 30)
    names = {}
    for item in (data or {}).get("items", []):
        ref = item.get("$ref")
        if not ref:
            continue
        ident = ref.rsplit("/", 1)[-1].split("?")[0]
        detail = _get(ref.replace("http://", "https://"),
                      cache_key="confitem-%s-%s" % (league, ident),
                      max_age_min=60 * 24 * 30)
        if detail and detail.get("id"):
            names[str(detail["id"])] = detail.get("shortName") or detail.get("name") or ""
    _conf_cache[league_path] = names
    return names


def standings(league, max_age_min=180):
    """Flat rows of {team, abbr, division, conference, seed, clincher, w/l/t}.

    No season parameter: ESPN then answers with the season in progress, which
    is what a daily run always wants. `clincher` is absent until late in a
    season, so a missing value means "not eliminated", never "eliminated".
    """
    sport = league["path"].split("/")[0]
    if sport == "soccer":
        return []  # table, not seeds -- the race logic does not apply
    url = "https://site.api.espn.com/apis/v2/sports/%s/standings" % league["path"]
    data = _get(url, {"level": 3}, cache_key="standings-%s" % league["key"],
                max_age_min=max_age_min)
    if not data:
        return []

    rows = []

    def walk(node, conference=None, division=None):
        name = node.get("name")
        entries = (node.get("standings") or {}).get("entries") or []
        for entry in entries:
            stats = {s.get("name"): s.get("displayValue") for s in entry.get("stats") or []}
            team = entry.get("team") or {}
            rows.append({
                "team": team.get("displayName") or "",
                "abbr": team.get("abbreviation") or "",
                "conference": conference or "",
                "division": division or name or "",
                "seed": _int(stats.get("playoffSeed")),
                "clincher": (stats.get("clincher") or "").lower(),
                "wins": _int(stats.get("wins")),
                "losses": _int(stats.get("losses")),
                "ties": _int(stats.get("ties")),
                "games_behind": stats.get("gamesBehind") or "",
                "points": _int(stats.get("points")),
            })
        for child in node.get("children") or []:
            # depth 1 is the conference, depth 2 the division
            if conference is None:
                walk(child, child.get("name"), None)
            else:
                walk(child, conference, child.get("name"))

    walk(data)
    return rows


def _int(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def clubs_in(league_path):
    """Set of lowercased club names in a competition, cached for a week.

    Used for "is either side English?" and "is either side an MLS club?" --
    the scoreboard payload does not say what country a club is from, but
    membership of eng.1 or usa.1 answers it well enough.
    """
    url = "%s/%s/teams" % (SITE, league_path)
    data = _get(url, {"limit": 100},
                cache_key="clubs-%s" % league_path.replace("/", "-"),
                max_age_min=60 * 24 * 7)
    names = set()
    try:
        entries = data["sports"][0]["leagues"][0]["teams"]
    except (KeyError, IndexError, TypeError):
        return names
    for entry in entries:
        team = entry.get("team") or {}
        for key in ("displayName", "shortDisplayName", "name", "abbreviation"):
            if team.get(key):
                names.add(team[key].strip().lower())
    return names


def soccer_table(league_path):
    """{lowercased club name: rank} for a league table, or {}."""
    url = "https://site.api.espn.com/apis/v2/sports/%s/standings" % league_path
    data = _get(url, cache_key="table-%s" % league_path.replace("/", "-"),
                max_age_min=180)
    out = {}

    def walk(node):
        entries = (node.get("standings") or {}).get("entries") or []
        for entry in entries:
            stats = {s.get("name"): s.get("displayValue") for s in entry.get("stats") or []}
            rank = _int(stats.get("rank"))
            name = (entry.get("team") or {}).get("displayName")
            if rank and name:
                out[name.strip().lower()] = rank
        for child in node.get("children") or []:
            walk(child)

    if data:
        walk(data)
    return out


def season_window(league):
    """(start, end) dates of the current REGULAR season, or (None, None).

    The season year comes from the standings payload already on disk, so this
    costs one extra request a week rather than one a run. Note the year is the
    season's own label -- the 2026-27 NHL season is year 2027.
    """
    sport = league["path"].split("/")[0]
    if sport == "soccer":
        return None, None
    url = "https://site.api.espn.com/apis/v2/sports/%s/standings" % league["path"]
    data = _get(url, {"level": 3}, cache_key="standings-%s" % league["key"],
                max_age_min=180)
    year = ((data or {}).get("season") or {}).get("year")
    if not year:
        return None, None
    league_path = league["path"].split("/")
    detail = _get("%s/%s/leagues/%s/seasons/%s/types/2" % (
        CORE, league_path[0], league_path[1], year),
        cache_key="season-%s-%s" % (league["key"], year), max_age_min=60 * 24 * 7)
    if not detail:
        return None, None

    def as_date(raw):
        try:
            return datetime.strptime((raw or "")[:10], "%Y-%m-%d").date()
        except ValueError:
            return None

    return as_date(detail.get("startDate")), as_date(detail.get("endDate"))


def team_list(league):
    """[(abbreviation, displayName)] for a league. Cached for a week.

    Used to validate the names typed into the control sheet -- a misspelled
    team silently matches nothing, which is indistinguishable from a quiet day.
    """
    url = "%s/%s/teams" % (SITE, league["path"])
    data = _get(url, {"limit": 1000}, cache_key="teams-%s" % league["key"],
                max_age_min=60 * 24 * 7)
    if not data:
        return []
    try:
        entries = data["sports"][0]["leagues"][0]["teams"]
    except (KeyError, IndexError):
        return []
    out = []
    for entry in entries:
        team = entry.get("team") or {}
        out.append((team.get("abbreviation") or "", team.get("displayName") or ""))
    return out


# --- normalization ----------------------------------------------------------

def _team(competitor):
    team = competitor.get("team") or {}
    rank = (competitor.get("curatedRank") or {}).get("current")
    record = ""
    for rec in competitor.get("records") or []:
        if rec.get("type") == "total":
            record = rec.get("summary") or ""
            break
    if not record:
        recs = competitor.get("records") or []
        record = (recs[0].get("summary") or "") if recs else ""
    return {
        "id": str(team.get("id") or ""),
        "abbr": team.get("abbreviation") or team.get("shortDisplayName") or "",
        "name": team.get("displayName") or team.get("name") or "",
        "short": team.get("shortDisplayName") or team.get("displayName") or "",
        # "Boise State", where shortDisplayName mangles it to "Boise St".
        "location": team.get("location") or "",
        "logo": team.get("logo") or "",
        # ESPN publishes a light version of every crest for dark backgrounds.
        # Verified: the default Tottenham badge averages luminance 35, the
        # dark-mode one 255 -- the first is invisible on our background.
        "logo_dark": (team.get("logo") or "").replace("/500/", "/500-dark/"),
        "color": team.get("color") or "",
        "alt_color": team.get("alternateColor") or "",
        "conference_id": str(team.get("conferenceId") or ""),
        "rank": rank if rank and rank != UNRANKED else None,
        "record": record,
        "score": competitor.get("score"),
    }


def _broadcasts(comp):
    """Returns (names, national_names, is_national).

    ESPN labels each broadcast market as national / home / away, which is what
    makes "national only" possible. Note MLB.TV is flagged national despite
    being a streaming service, so the hide list still matters.
    """
    names, national_names, national = [], [], False
    by_market = {"home": [], "away": []}
    for entry in comp.get("broadcasts") or []:
        market = (entry.get("market") or "").lower()
        is_nat = market == "national"
        for name in entry.get("names") or []:
            if name not in names:
                names.append(name)
            if is_nat and name not in national_names:
                national_names.append(name)
            if market in by_market and name not in by_market[market]:
                by_market[market].append(name)
        if is_nat:
            national = True
    if not names:
        for geo in comp.get("geoBroadcasts") or []:
            name = (geo.get("media") or {}).get("shortName")
            if name and name not in names:
                names.append(name)
            if ((geo.get("market") or {}).get("type") or "").lower() == "national":
                national = True
                if name and name not in national_names:
                    national_names.append(name)
    return names, national_names, national, by_market


def _odds(comp):
    """-> (details, over_under, favourite_side, label).

    `details` is the provider's own wording ("IU -40.5") and stays the source
    for the blowout rule. The other two say which team the line belongs to and
    how to write it, which differs by sport:

    * Point-spread sports flag the favourite per side, and `spread` is signed
      from the home team, so the favourite always reads as minus its
      magnitude -- no abbreviation matching needed.
    * Soccer has neither field. Only `details` carries anything, holding
      either a three-way moneyline ("LIV -205") or an Asian handicap
      ("TOT -0.5"), and the team is named by abbreviation. That abbreviation
      is ESPN's own, so it matches the competitors exactly -- verified across
      33 priced fixtures, all 33 matched. Only the moneylines are kept, and
      they are labelled ML so they cannot be read as points; a moneyline is
      100 or more in magnitude, a handicap always less.
    """
    # The odds list itself can contain nulls (seen on college football).
    odds = [o for o in (comp.get("odds") or []) if isinstance(o, dict)]
    if not odds:
        return "", "", "", ""
    first = odds[0]
    details = (first.get("details") or "").strip()
    over_under = first.get("overUnder")
    over_under = "O/U %s" % over_under if over_under is not None else ""

    for name in ("home", "away"):
        if (first.get("%sTeamOdds" % name) or {}).get("favorite"):
            points = first.get("spread")
            if isinstance(points, (int, float)):
                # Always a decimal place: "-7" and "-7.5" side by side read
                # as different kinds of number. Moneylines below are whole by
                # nature and keep no decimal.
                return details, over_under, name, "-%.1f" % abs(points)
            break

    match = re.match(r"^(.+?)\s+([+-]\d+(?:\.\d+)?)$", details)
    if match:
        token, value = match.group(1).strip(), float(match.group(2))
        # Only moneylines, which are 100 or more in magnitude. The rest are
        # Asian handicaps -- half-goal lines in a sport that scores in ones,
        # which read as nonsense next to a point spread.
        if abs(value) >= 100:
            for competitor in comp.get("competitors") or []:
                if ((competitor.get("team") or {}).get("abbreviation") or "") == token:
                    # To the nearest five, as every other price here is. Books
                    # quote moneylines in fives anyway, so this almost never
                    # moves a number -- it stops the odd one that is not from
                    # looking like a different kind of figure.
                    return (details, over_under, competitor.get("homeAway") or "",
                            "%+d ML" % (int(round(value / 5.0)) * 5))

    return details, over_under, "", ""


def american_value(decimal_price):
    """Decimal odds as a signed American number: 2.15 -> 115.0, 1.5 -> -200.0."""
    if decimal_price >= 2:
        return (decimal_price - 1) * 100
    return -100 / (decimal_price - 1)


def _american(decimal_price, nearest=1):
    """Decimal odds as an American moneyline: 2.15 -> +115, 1.5 -> -200.

    `nearest` rounds the result, which is for DERIVED prices only. A quoted
    moneyline is the book's own number and is printed as given; a double
    chance is worked out here from three prices, so its last digit is
    arithmetic rather than anything anyone is offering.
    """
    value = american_value(decimal_price)
    if nearest > 1:
        value = round(value / float(nearest)) * nearest
    return "%+d" % round(value)


def _decimal_price(entry):
    """Decimal odds from either shape ESPN uses, or None.

    DraftKings publishes an American `moneyLine`; Bet 365 publishes fractional
    odds already reduced to a decimal `value`. Both are normalised to decimal
    so prices can be compared across providers.
    """
    money = entry.get("moneyLine")
    if isinstance(money, (int, float)) and money:
        return 1 + (money / 100.0 if money > 0 else 100.0 / -money)
    value = ((entry.get("odds") or {}).get("value"))
    if isinstance(value, (int, float)) and value > 1:
        return float(value)
    return None


def three_way(league, event_id, competition_id):
    """{'home': d, 'away': d, 'draw': d} as decimal odds, or {}.

    Soccer is a three-outcome market and the scoreboard carries only one leg
    of it, so anything that needs the draw -- a double chance, or a price for
    the side that is not favourite -- has to come from the core API.

    The first provider pricing ALL THREE wins. A provider missing the draw is
    no use: two legs cannot be combined into a bet that covers two outcomes,
    and quietly falling back to a different provider for the missing leg would
    mix two books' margins into one number.
    """
    path = league.get("path") or ""
    if "/" not in path:
        return {}
    sport, code = path.split("/", 1)
    data = _get("%s/%s/leagues/%s/events/%s/competitions/%s/odds"
                % (CORE, sport, code, event_id, competition_id),
                {"limit": 20}, cache_key="odds3-%s-%s" % (code, event_id),
                max_age_min=180)
    for item in (data or {}).get("items") or []:
        prices = {}
        for key, side in (("homeTeamOdds", "home"), ("awayTeamOdds", "away"),
                          ("drawOdds", "draw")):
            price = _decimal_price(item.get(key) or {})
            if price:
                prices[side] = price
        if len(prices) == 3:
            return prices
    return {}


def double_chance(team_price, draw_price):
    """Decimal odds for 'this side wins OR draws'.

    Two outcomes of the three, so the implied probabilities add:
    1/((1/a) + (1/b)), which reduces to the usual ab/(a+b). The book's margin
    rides along in both legs, so this sits slightly shorter than a book's own
    double-chance price -- it is derived from the three-way market, not quoted.
    """
    if not team_price or not draw_price:
        return None
    return (team_price * draw_price) / (team_price + draw_price)


def event_moneyline(league, event_id, competition_id):
    """-> (side, label) for a fixture the scoreboard priced only as a handicap.

    The scoreboard carries one provider and sometimes only its handicap, which
    is no use here. The core API returns every provider and the full three-way
    market, so a moneyline can usually still be found. Only asked for when the
    scoreboard gave nothing -- twice in a fifteen-day window -- so the extra
    request is rare enough not to matter.

    A provider is only trusted when it prices BOTH sides: given one price
    alone there is no way to tell a favourite from an underdog.
    """
    path = league.get("path") or ""
    if "/" not in path:
        return "", ""
    sport, code = path.split("/", 1)
    data = _get("%s/%s/leagues/%s/events/%s/competitions/%s/odds"
                % (CORE, sport, code, event_id, competition_id),
                {"limit": 20}, cache_key="odds-%s-%s" % (code, event_id),
                max_age_min=180)
    for item in (data or {}).get("items") or []:
        prices = {}
        for side in ("home", "away"):
            price = _decimal_price(item.get("%sTeamOdds" % side) or {})
            if price:
                prices[side] = price
        if len(prices) == 2:
            side = min(prices, key=prices.get)
            return side, "%s ML" % _american(prices[side], 5)
    return "", ""


def _aggregate(comp, home, away):
    """Two-legged aggregate as '3-1 ARS', or '1-1 agg' when level.

    Built from series.competitors rather than the prose headline, so the
    figures are ESPN's own and the leader is identified by team id.
    """
    series = comp.get("series") or {}
    entries = [c for c in series.get("competitors") or []
               if isinstance(c.get("aggregateScore"), (int, float))]
    if len(entries) != 2:
        return ""
    entries.sort(key=lambda c: c["aggregateScore"], reverse=True)
    top, bottom = entries
    scores = "%g-%g" % (top["aggregateScore"], bottom["aggregateScore"])
    if top["aggregateScore"] == bottom["aggregateScore"]:
        return "%s agg" % scores
    by_id = {t["id"]: t for t in (home, away) if t.get("id")}
    leader = by_id.get(str(top.get("id") or ""))
    return "%s %s" % (scores, leader["abbr"]) if leader else "%s agg" % scores


def _parse_start(raw):
    for fmt in ("%Y-%m-%dT%H:%MZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%MZ"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def games_for(league, date_yyyymmdd, tz, cache_minutes=30):
    """Normalized game dicts for one league on one date (local to tz).

    A league may declare several param sets. College football needs two: FBS
    lives in groups=80 and FCS in groups=81, and an Ivy League team like
    Cornell is invisible to the FBS call.
    """
    variants = league.get("params_variants") or [{"params": league.get("params") or {}}]
    url = "%s/%s/scoreboard" % (SITE, league["path"])
    events, seen = [], set()
    for index, variant in enumerate(variants):
        params = dict(variant.get("params") or {})
        label = variant.get("label") or ""
        params["dates"] = date_yyyymmdd
        suffix = "" if len(variants) == 1 else "-v%d" % index
        data = _get(url, params,
                    cache_key="%s%s-%s" % (league["key"], suffix, date_yyyymmdd),
                    max_age_min=cache_minutes)
        for event in (data or {}).get("events") or []:
            if event.get("id") not in seen:
                seen.add(event.get("id"))
                event["_source"] = label      # which feed answered: FBS vs FCS
                events.append(event)
    if not events:
        return []

    conf_names = {}
    out = []
    for event in events:
        comps = event.get("competitions") or []
        if not comps:
            continue
        comp = comps[0]
        start = _parse_start(event.get("date") or "")
        if not start:
            continue
        local = start.astimezone(tz)

        home = away = None
        for competitor in comp.get("competitors") or []:
            side = _team(competitor)
            if competitor.get("homeAway") == "home":
                home = side
            else:
                away = side
        if not home or not away:
            continue

        group = comp.get("groups") or {}
        conference = group.get("shortName") if group.get("isConference") else ""
        if not conference and league["path"] in _CONF_ROOT:
            if not conf_names:
                conf_names = conference_names(league["path"])
            found = {conf_names.get(t["conference_id"], "") for t in (home, away)}
            conference = " / ".join(sorted(found - {""}))

        tv, tv_national, national, tv_market = _broadcasts(comp)
        spread, over_under, spread_side, spread_label = _odds(comp)
        status = (comp.get("status") or {}).get("type") or {}
        # Soccer fixtures are sometimes priced only as a handicap here, which
        # says nothing a reader wants. The full market is one request away.
        if (not spread_label and spread and (league.get("sport") or "") == "Soccer"
                and (status.get("state") or "pre") == "pre"):
            spread_side, spread_label = event_moneyline(
                league, event.get("id") or "", comp.get("id") or "")
        notes = [n.get("headline") for n in comp.get("notes") or [] if n.get("headline")]

        out.append({
            "league": league["key"],
            "league_label": league["label"],
            "sport": league.get("sport") or "",
            "id": event.get("id"),
            "start_utc": start,
            "start_local": local,
            "state": status.get("state") or "pre",
            "postseason": (event.get("season") or {}).get("type") == 3,
            # Numeric for the US leagues (1 = preseason); soccer uses its own
            # ids, so the slug below is the reliable marker there.
            "season_type": (event.get("season") or {}).get("type"),
            "source": event.get("_source") or "",
            # Soccer has no 1/2/3 season types; the phase lives here instead,
            # e.g. "league-phase", "round-of-16", "mls-cup", "final".
            "round": ((event.get("season") or {}).get("slug") or ""),
            "status_detail": status.get("shortDetail") or "",
            # A delay keeps state "in" and buries the period in prose --
            # "Rain Delay, Top 1st". The period is carried separately so the
            # page can say which part of the game it stopped in, whatever the
            # reason: STATUS_RAIN_DELAY and STATUS_DELAYED both match.
            "delayed": "DELAY" in (status.get("name") or "").upper(),
            # A game that produced no result. ESPN files these as state
            # "post", which would otherwise read as "Final" -- and at 0-0 the
            # draw rule would italicise both sides of a game never played.
            "called_off": any(word in (status.get("name") or "").upper()
                              for word in ("POSTPONED", "CANCEL", "SUSPEND")),
            "status_note": status.get("description") or "",
            "period": (comp.get("status") or {}).get("period"),
            # Seconds left in the period. Basketball counts halves, so "ten
            # minutes in" is only expressible as a clock, not a period.
            "clock": (comp.get("status") or {}).get("clock"),
            "home": home,
            "away": away,
            "tv": tv,
            "tv_national": tv_national,
            # The regional feed for each side, so a favourite can show its own.
            "tv_home": tv_market["home"],
            "tv_away": tv_market["away"],
            "national": national,
            # Series state for a playoff tie: "LAD lead series 2-1".
            "series": ((comp.get("series") or {}).get("summary") or ""),
            "aggregate": _aggregate(comp, home, away),
            "spread": spread,
            "spread_side": spread_side,
            "spread_label": spread_label,
            "over_under": over_under,
            "conference": conference,
            "neutral": bool(comp.get("neutralSite")),
            "venue": (comp.get("venue") or {}).get("fullName") or "",
            "note": notes[0] if notes else "",
            "link": "https://www.espn.com/%s/game/_/gameId/%s" % (
                league["path"].split("/")[0], event.get("id")),
        })
    return out
