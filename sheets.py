"""The Google Sheet control surface.

Two tabs drive everything you change day to day:

  Teams    Sport | Team | Tier | Note | Expires
  Options  Scope | Option | Value | Notes

Read over the gviz CSV endpoint, which needs no credentials -- the sheet just
has to be shared "anyone with the link can view". Deliberately not gspread:
that pulls in cryptography, which is exactly what broke on this win-arm64 box
during the dynasty rebuild.

Every fetch is cached. If the sheet is unreachable the last good copy is used
rather than silently reverting to an empty list, because an empty watchlist
looks identical to a working one with nothing in it.
"""

import csv
import io
import os
import re
import time
from datetime import date, datetime

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")

GVIZ = "https://docs.google.com/spreadsheets/d/%s/gviz/tq?tqx=out:csv&sheet=%s"

TIER_FAVORITE = "favorite"
TIER_FOLLOW = "follow"   # pinned like a favorite, but never drives the race
TIER_WATCH = "watch"

# Sport column -> league key in config.json. Spellings people actually type.
SPORT_ALIASES = {
    "nfl": "nfl", "football": "nfl",
    "nba": "nba", "basketball": "nba",
    "mlb": "mlb", "baseball": "mlb",
    "nhl": "nhl", "hockey": "nhl",
    "epl": "epl", "premier league": "epl", "premier": "epl", "soccer": "epl",
    "mls": "mls", "usmnt": "usmnt", "usa": "usmnt",
    "ucl": "ucl", "uel": "uel", "uecl": "uecl",
    "fa cup": "facup", "efl": "eflcup", "carabao": "eflcup",
    "cfb": "college-football", "college football": "college-football",
    "ncaaf": "college-football",
    "cbb": "mens-college-basketball", "college basketball": "mens-college-basketball",
    "ncaab": "mens-college-basketball",
    "chky": "mens-college-hockey", "college hockey": "mens-college-hockey",
    "ncaah": "mens-college-hockey",
}

TRUE_WORDS = {"true", "yes", "y", "1", "on"}
FALSE_WORDS = {"false", "no", "n", "0", "off"}

BOOL_OPTIONS = {
    "enabled", "show_all_games", "national_tv_only", "standalone_only",
    "include_postseason", "playoff_race", "race_only_last_spot",
    "race_until_settled", "race_until_season_end",
    "hide_finished", "show_odds", "show_records",
}
INT_OPTIONS = {"race_from_month", "race_until_month", "playoff_spots",
               "race_min_odds", "race_last_days"}
TEXT_OPTIONS = {"timezone"}


class SheetError(Exception):
    pass


def sheet_id_from(raw):
    """Accept a bare id or a pasted spreadsheet URL."""
    raw = (raw or "").strip()
    if not raw:
        return ""
    match = re.search(r"/spreadsheets/d/([A-Za-z0-9-_]+)", raw)
    return match.group(1) if match else raw


def _cache_file(tab):
    return os.path.join(CACHE, "sheet-%s.csv" % re.sub(r"\W+", "", tab).lower())


def fetch_tab(sheet_id, tab, cache_minutes=120):
    """CSV text for one tab. Falls back to the cached copy on any failure."""
    os.makedirs(CACHE, exist_ok=True)
    path = _cache_file(tab)
    if os.path.exists(path):
        age_min = (time.time() - os.path.getmtime(path)) / 60
        if age_min < cache_minutes:
            with open(path, encoding="utf-8") as fh:
                return fh.read(), "cache"
    url = GVIZ % (sheet_id, requests.utils.quote(tab))
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        text = resp.text
        # A private sheet answers 200 with a sign-in page, not CSV.
        if text.lstrip().lower().startswith("<!doctype") or "<html" in text[:400].lower():
            raise SheetError("sheet is not shared publicly (got a sign-in page)")
    except Exception as exc:
        if os.path.exists(path):
            print("  ! sheet tab %r unreadable (%s); using last good copy" % (tab, exc))
            with open(path, encoding="utf-8") as fh:
                return fh.read(), "stale"
        print("  ! sheet tab %r unreadable (%s); no cached copy" % (tab, exc))
        return None, "missing"
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    return text, "fresh"


def _rows(text):
    """CSV text -> list of dicts with lowercased, stripped keys."""
    if not text:
        return []
    reader = csv.DictReader(io.StringIO(text))
    out = []
    for row in reader:
        clean = {}
        for key, value in row.items():
            if key is None:
                continue
            clean[key.strip().lower()] = (value or "").strip()
        if any(clean.values()):
            out.append(clean)
    return out


def _truthy(value):
    lowered = (value or "").strip().lower()
    if lowered in TRUE_WORDS:
        return True
    if lowered in FALSE_WORDS:
        return False
    return None


def _expired(raw, today=None):
    """True if an Expires cell is a date that has already passed."""
    raw = (raw or "").strip()
    if not raw:
        return False
    today = today or date.today()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d %b %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(raw, fmt).date() < today
        except ValueError:
            continue
    print("  ! could not read expiry date %r; keeping the row" % raw)
    return False


def parse_teams(text, warn=True):
    """-> {league_key: {"favorite": [entries], "watch": [entries]}}."""
    result = {}
    for row in _rows(text):
        sport = SPORT_ALIASES.get(row.get("sport", "").lower())
        team = row.get("team", "")
        if not team:
            continue
        if not sport:
            if warn and row.get("sport"):
                print("  ! unknown sport %r in Teams tab; row skipped" % row.get("sport"))
            continue
        if _expired(row.get("expires")):
            continue
        raw_tier = (row.get("tier") or "").strip().lower()
        if raw_tier.startswith("fav"):
            tier = TIER_FAVORITE
        elif raw_tier.startswith("fol"):
            tier = TIER_FOLLOW
        else:
            tier = TIER_WATCH
        bucket = result.setdefault(
            sport, {TIER_FAVORITE: [], TIER_FOLLOW: [], TIER_WATCH: []})
        bucket[tier].append({
            "team": team,
            "note": row.get("note", ""),
            "expires": row.get("expires", ""),
        })
    return result


def parse_options(text, warn=True):
    """-> {"all": {...}, league_key: {...}} with typed values."""
    result = {"all": {}}
    for row in _rows(text):
        option = (row.get("option") or "").strip().lower().replace(" ", "_")
        if not option:
            continue
        scope_raw = (row.get("scope") or "all").strip().lower()
        scope = "all" if scope_raw in ("", "all", "global", "everything") \
            else SPORT_ALIASES.get(scope_raw)
        if not scope:
            if warn:
                print("  ! unknown scope %r in Options tab; row skipped" % scope_raw)
            continue
        raw = row.get("value", "")
        if option in BOOL_OPTIONS:
            value = _truthy(raw)
            if value is None:
                if warn:
                    print("  ! option %r wants TRUE/FALSE, got %r; row skipped"
                          % (option, raw))
                continue
        elif option in INT_OPTIONS:
            try:
                value = int(float(raw))
            except (TypeError, ValueError):
                if warn:
                    print("  ! option %r wants a number, got %r; row skipped"
                          % (option, raw))
                continue
        elif option in TEXT_OPTIONS:
            value = raw
        else:
            if warn:
                print("  ! unknown option %r; row skipped" % option)
            continue
        result.setdefault(scope, {})[option] = value
    return result


def apply_to_config(config, teams, options):
    """Fold sheet contents into the in-memory config.

    The sheet wins over config.json for everything it specifies, and stays
    silent about everything it does not -- so a blank cell is "leave it alone",
    never "turn it off".
    """
    favorites, following, watchlist = {}, {}, {}
    for league_key, buckets in (teams or {}).items():
        favorites[league_key] = [e["team"] for e in buckets[TIER_FAVORITE]]
        following[league_key] = [e["team"] for e in buckets[TIER_FOLLOW]]
        watchlist[league_key] = buckets[TIER_WATCH]
    config["favorites"] = favorites or dict(config.get("favorites") or {})
    config["following"] = following or dict(config.get("following") or {})
    config["watchlist"] = watchlist

    options = options or {}
    glob = options.get("all", {})
    if glob.get("timezone"):
        config["timezone"] = glob["timezone"]
    for key in ("hide_finished", "show_odds", "show_records"):
        if key in glob:
            config[key] = glob[key]

    for league in config.get("leagues", []):
        merged = dict(glob)
        merged.update(options.get(league["key"], {}))
        if "enabled" in merged:
            league["enabled"] = merged["enabled"]
        include = dict(league.get("include") or {})
        include["favorites"] = True  # favorites always qualify
        if "show_all_games" in merged:
            include["all"] = merged["show_all_games"]
        if "national_tv_only" in merged:
            include["national_tv"] = merged["national_tv_only"]
            if merged["national_tv_only"]:
                include["all"] = False
        if "standalone_only" in merged:
            include["standalone_only"] = merged["standalone_only"]
            if merged["standalone_only"]:
                include["all"] = False
        if "include_postseason" in merged:
            include["include_postseason"] = merged["include_postseason"]
        league["include"] = include
        for key in ("hide_finished", "show_odds", "show_records",
                    "playoff_race", "race_from_month", "race_until_month",
                    "playoff_spots", "race_min_odds", "race_last_days",
                    "race_only_last_spot", "race_until_settled",
                    "race_until_season_end"):
            if key in merged:
                league[key] = merged[key]
    return config


def expand_groups(config):
    """Share one team list across a group of competitions.

    Tottenham is listed once under EPL, not six times for the league, both
    domestic cups and the three European competitions. A league declares
    `team_group` and inherits that group's favorites, follows and watchlist.
    """
    for league in config.get("leagues", []):
        group = league.get("team_group")
        if not group or group == league["key"]:
            continue
        for bucket in ("favorites", "following"):
            shared = (config.get(bucket) or {}).get(group) or []
            if shared:
                target = config.setdefault(bucket, {}).setdefault(league["key"], [])
                target.extend(t for t in shared if t not in target)
        shared_watch = (config.get("watchlist") or {}).get(group) or []
        if shared_watch:
            target = config.setdefault("watchlist", {}).setdefault(league["key"], [])
            have = {(e.get("team") or "").lower() for e in target}
            target.extend(e for e in shared_watch
                          if (e.get("team") or "").lower() not in have)
    return config


def load(config, use_sheet=True):
    """Read the sheet (if configured) and merge it into config. Returns notes."""
    control = config.get("control_sheet") or {}
    sheet_id = sheet_id_from(control.get("sheet_id"))
    if not use_sheet or not sheet_id:
        # config.json is the source of truth; nothing to merge, just normalise.
        config["favorites"] = dict(config.get("favorites") or {})
        config["following"] = dict(config.get("following") or {})
        config["watchlist"] = {
            key: [dict(entry) for entry in entries]
            for key, entries in (config.get("watchlist") or {}).items()}
        expand_groups(config)
        return ["sheet not used; running on config.json values"]

    minutes = control.get("cache_minutes", 120)
    teams_text, teams_src = fetch_tab(sheet_id, control.get("teams_tab", "Teams"), minutes)
    opts_text, opts_src = fetch_tab(sheet_id, control.get("options_tab", "Options"), minutes)
    apply_to_config(config, parse_teams(teams_text), parse_options(opts_text))
    expand_groups(config)

    notes = []
    if "stale" in (teams_src, opts_src):
        notes.append("sheet unreachable - using the last copy that worked")
    elif "missing" in (teams_src, opts_src):
        notes.append("sheet unreadable and never cached - using config.json values")
    return notes
