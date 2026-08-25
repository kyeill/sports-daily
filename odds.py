"""Playoff odds, used to decide whether a race is worth showing at all.

Sources differ per league because no single one covers everything:

  NFL  ESPN FPI   probmakeplayoffs   0-100
  NBA  ESPN BPI   probmakeplayoffs   0-100
  MLB  FanGraphs  endData.poffTitle  0-1, scaled here
  NHL  nothing usable -- MoneyPuck, the obvious source, explicitly asks not to
       be scraped, so the NHL falls back to standings position instead

Cached for half a day: these move once a day at most, and FanGraphs is somebody
else's bandwidth.
"""

import espn

ESPN_POWERINDEX = "https://site.web.api.espn.com/apis/fitt/v3/sports/%s/powerindex"
FANGRAPHS = ("https://www.fangraphs.com/api/playoff-odds/odds"
             "?dateDelta=&projectionMode=2&standingsType=div")

CACHE_MINUTES = 60 * 12


def _flat(text):
    return "".join(c for c in (text or "").lower() if c.isalnum())


def same_team(name, abbr, target):
    """Match a source's team label against a config entry.

    Looser than the game-matching rule on purpose: sources disagree about how
    much of a name to give. FanGraphs says "Tigers" where the config says
    "Detroit Tigers", so containment has to work in both directions.
    """
    flat_target = _flat(target)
    if not flat_target:
        return False
    if flat_target == _flat(abbr):
        return True
    flat_name = _flat(name)
    if not flat_name:
        return False
    return flat_target in flat_name or flat_name in flat_target


def _espn_odds(league):
    data = espn._get(ESPN_POWERINDEX % league["path"],
                     cache_key="odds-%s" % league["key"],
                     max_age_min=CACHE_MINUTES)
    if not data:
        return {}
    names = []
    for category in data.get("categories") or []:
        if category.get("name") == "projections":
            names = category.get("names") or []
            break
    if "probmakeplayoffs" not in names:
        return {}
    index = names.index("probmakeplayoffs")
    out = {}
    for entry in data.get("teams") or []:
        team = entry.get("team") or {}
        for category in entry.get("categories") or []:
            if category.get("name") != "projections":
                continue
            values = category.get("values") or []
            if index < len(values) and isinstance(values[index], (int, float)):
                out[team.get("displayName") or ""] = (
                    float(values[index]), team.get("abbreviation") or "")
    return out


def _fangraphs_odds(_league):
    data = espn._get(FANGRAPHS, cache_key="odds-mlb", max_age_min=CACHE_MINUTES)
    if not isinstance(data, list):
        return {}
    out = {}
    for row in data:
        end = row.get("endData") or {}
        value = end.get("poffTitle")
        if isinstance(value, (int, float)):
            # FanGraphs reports a 0-1 probability; everything else is a percent.
            out[row.get("shortName") or ""] = (float(value) * 100,
                                               row.get("abbName") or "")
    return out


SOURCES = {
    "nfl": _espn_odds,
    "nba": _espn_odds,
    "mlb": _fangraphs_odds,
    # College football's FPI carries probmakeplayoffs too (CFP odds), so the
    # same reader works if college is added back.
    "college-football": _espn_odds,
}


def playoff_odds(league):
    """{team_label: (percent, abbr)} for a league, or {} when unavailable."""
    source = SOURCES.get(league["key"])
    if not source:
        return {}
    try:
        return source(league)
    except Exception as exc:  # a third party changing shape must not break the run
        print("  ! playoff odds unavailable for %s (%s)" % (league["label"], exc))
        note = "%s odds" % league["label"]
        if note not in espn.FAILURES:
            espn.FAILURES.append(note)
        return {}


def odds_for(league, team_names):
    """Percent for the first of team_names the source recognises, else None."""
    table = playoff_odds(league)
    if not table:
        return None
    for target in team_names:
        for label, (percent, abbr) in table.items():
            if same_team(label, abbr, target):
                return percent
    return None
