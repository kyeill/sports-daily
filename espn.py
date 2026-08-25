"""Fetch and normalize ESPN's public scoreboard API into plain dicts.

One request per configured league per day. Responses are cached on disk so
repeated runs (and re-renders) do not re-hit the API.

Verified payload shapes on 2026-08-24 -- see README for the trap list.
"""

import json
import os
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
        "abbr": team.get("abbreviation") or team.get("shortDisplayName") or "",
        "name": team.get("displayName") or team.get("name") or "",
        "short": team.get("shortDisplayName") or team.get("displayName") or "",
        "logo": team.get("logo") or "",
        "color": team.get("color") or "",
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
    for entry in comp.get("broadcasts") or []:
        is_nat = (entry.get("market") or "").lower() == "national"
        for name in entry.get("names") or []:
            if name not in names:
                names.append(name)
            if is_nat and name not in national_names:
                national_names.append(name)
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
    return names, national_names, national


def _odds(comp):
    # The odds list itself can contain nulls (seen on college football).
    odds = [o for o in (comp.get("odds") or []) if isinstance(o, dict)]
    if not odds:
        return "", ""
    first = odds[0]
    details = first.get("details") or ""
    over_under = first.get("overUnder")
    return details, ("O/U %s" % over_under if over_under is not None else "")


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

        tv, tv_national, national = _broadcasts(comp)
        spread, over_under = _odds(comp)
        status = (comp.get("status") or {}).get("type") or {}
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
            "home": home,
            "away": away,
            "tv": tv,
            "tv_national": tv_national,
            "national": national,
            # Series state for a playoff tie: "LAD lead series 2-1".
            "series": ((comp.get("series") or {}).get("summary") or ""),
            "national_only": bool(league.get("national_only_display")),
            "spread": spread,
            "over_under": over_under,
            "conference": conference,
            "neutral": bool(comp.get("neutralSite")),
            "venue": (comp.get("venue") or {}).get("fullName") or "",
            "note": notes[0] if notes else "",
            "link": "https://www.espn.com/%s/game/_/gameId/%s" % (
                league["path"].split("/")[0], event.get("id")),
        })
    return out
