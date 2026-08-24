"""Derive the playoff-race half of the watchlist from live standings.

The manual watchlist in the sheet covers rivalries and hunches. This covers the
part that changes weekly on its own: who your team is actually competing with
for a spot. Two teams at most, so it never floods the page.

For a favorite team, it follows:
  * the leader of your division -- the team you have to catch, or the one
    catching you (skipped when that is your own team)
  * the team holding the last playoff spot -- or, if that is your team, the
    first team on the outside looking in

Switched off entirely once ESPN marks your team eliminated, and before
`race_from_month`, because in September everyone is one game out of everything.
"""

from datetime import date, timedelta

import espn
import filters
import odds

ELIMINATED = "e"


def _favorite_row(rows, favorites):
    """Match in the order the favorites are listed, not standings order.

    With two favorites in one league (Pistons and Cavaliers), standings order
    would hand the race to whichever happened to sit higher that week.
    """
    for fav in favorites:
        for row in rows:
            team = {"abbr": row["abbr"], "name": row["team"], "short": row["team"]}
            if filters._matches(team, fav):
                return row
    return None


def _in_window(league, today):
    """True when the race should be live on this date.

    `race_last_days` counts back from the real end of the regular season, so
    "the final month" tracks the schedule instead of guessing at a month
    number. Falls back to the month window when the dates are unavailable.
    """
    if league.get("race_until_season_end"):
        _, end = espn.season_window(league)
        if end:
            # Anchor the start to the season's OWN final stretch: March 1 of
            # the year that season ends. Testing month >= 3 on its own would
            # switch the race back on in October, when the next season starts
            # and its April end date is still in the future.
            start = date(end.year, league.get("race_from_month", 3), 1)
            return start <= today <= end
    last_days = league.get("race_last_days")
    if last_days:
        _, end = espn.season_window(league)
        if end:
            return (end - timedelta(days=last_days)) <= today <= end
    start_month = league.get("race_from_month", 11)
    end_month = league.get("race_until_month", 2)
    # Football's window wraps the year end (Nov->Feb); baseball's does not
    # (Jul->Oct). Testing every window as a wrap makes the second one always
    # true, which would leave the race running in March.
    if start_month <= end_month:
        return start_month <= today.month <= end_month
    return today.month >= start_month or today.month <= end_month


def gap(mine, other, use_points=False):
    """How far your team sits behind another, phrased for the sport.

    Hockey is played for points, not a win column, so games back is meaningless
    there; everywhere else the standard formula applies. The choice comes from
    the league, not from whether a `points` field happens to exist -- today only
    the NHL carries one, but that is not a guarantee.
    """
    if use_points and mine.get("points") is not None and other.get("points") is not None:
        diff = (other["points"] or 0) - (mine["points"] or 0)
        if diff > 0:
            return "%d pts back" % diff
        return "level on points" if diff == 0 else "%d pts ahead" % -diff
    for row in (mine, other):
        if row.get("wins") is None or row.get("losses") is None:
            return ""
    back = ((other["wins"] - mine["wins"]) + (mine["losses"] - other["losses"])) / 2.0
    if back > 0:
        return ("%.1f" % back).rstrip("0").rstrip(".") + " GB"
    if back == 0:
        return "level"
    return ("%.1f" % -back).rstrip("0").rstrip(".") + " ahead"


def _seeded(rows):
    return [r for r in rows if r.get("seed")]


def derive(config, league, today=None):
    """-> [{team, note}] for the league, or [] when the race is not live."""
    league["_race"] = {"active": False, "percent": None, "team": ""}
    if not league.get("playoff_race"):
        return []
    favorites = filters.favorites_for(config, league["key"])
    if not favorites:
        return []
    league["_race"]["team"] = favorites[0]

    today = today or date.today()
    if not _in_window(league, today):
        return []

    rows = espn.standings(league)
    if not rows:
        return []
    mine = _favorite_row(rows, favorites)
    if not mine or mine.get("clincher") == ELIMINATED:
        return []
    # Any clinch marker at all means the question is settled -- clinched a spot
    # or knocked out, either way there is nothing left to chase.
    if league.get("race_until_settled") and mine.get("clincher"):
        return []

    # A playoff-odds floor, where a source exists. ESPN's elimination flag
    # arrives far too late to be the only test -- a team can be mathematically
    # alive and practically finished for weeks.
    percent = odds.odds_for(league, favorites)
    league["_race"]["percent"] = percent
    floor = league.get("race_min_odds")
    # No source (the NHL) means the floor cannot be applied; standings position
    # is the fallback, and ignoring the floor beats showing nothing.
    if floor and percent is not None and percent < floor:
        return []
    league["_race"]["active"] = True

    points_league = (league.get("sport") or "").lower() == "hockey"
    out, seen = [], {mine["team"]}
    spots = league.get("playoff_spots", 7)

    division = sorted([r for r in _seeded(rows) if r["division"] == mine["division"]],
                      key=lambda r: r["seed"])
    if division and not league.get("race_only_last_spot"):
        leader = division[0]
        # When your team IS the leader, the interesting one is the chaser.
        rival = (division[1] if len(division) > 1 else None) \
            if leader["team"] in seen else leader
        if rival and rival["team"] not in seen:
            out.append({"team": rival["team"], "note": "Division Chase",
                        "context": _context(mine, rival, points_league)})
            seen.add(rival["team"])

    conference = [r for r in _seeded(rows) if r["conference"] == mine["conference"]]
    by_seed = {r["seed"]: r for r in conference}
    # Whoever holds the last spot -- or the first team out, when it is yours.
    target = by_seed.get(spots + 1 if mine.get("seed") == spots else spots)
    if target and target["team"] not in seen:
        out.append({"team": target["team"],
                    "note": league.get("race_spot_label") or "Wild Card Chase",
                    "context": _context(mine, target, points_league)})

    return out


def _context(mine, other, use_points=False):
    """Just the gap: "2 GB", "6 pts back". The team is obvious from the row."""
    return gap(mine, other, use_points)


def snapshot(config, league):
    """Today's standing for a favorite, for the history file. None if n/a.

    Deliberately ignores the race window and the odds floor: the point of a
    history is that it keeps recording while the season is dull, because a gap
    you did not write down cannot be recovered later.
    """
    favorites = filters.favorites_for(config, league["key"])
    if not favorites:
        return None
    rows = espn.standings(league)
    if not rows:
        return None
    mine = _favorite_row(rows, favorites)
    if not mine:
        return None

    points_league = (league.get("sport") or "").lower() == "hockey"
    spots = league.get("playoff_spots", 7)
    division = sorted([r for r in _seeded(rows) if r["division"] == mine["division"]],
                      key=lambda r: r["seed"])
    leader = division[0] if division else None
    conference = [r for r in _seeded(rows) if r["conference"] == mine["conference"]]
    holder = {r["seed"]: r for r in conference}.get(spots)

    return {
        "team": mine["team"],
        "seed": mine.get("seed") or "",
        "division": mine.get("division") or "",
        "wins": mine.get("wins") if mine.get("wins") is not None else "",
        "losses": mine.get("losses") if mine.get("losses") is not None else "",
        "points": mine.get("points") if mine.get("points") is not None else "",
        "clincher": mine.get("clincher") or "",
        "leads_division": "yes" if leader and leader["team"] == mine["team"] else "no",
        "gap_to_division": "" if not leader or leader["team"] == mine["team"]
                           else gap(mine, leader, points_league),
        "gap_to_last_spot": "" if not holder or holder["team"] == mine["team"]
                            else gap(mine, holder, points_league),
    }


def status(league):
    """One line about the race: its odds when live, why it is quiet when not."""
    state = league.get("_race") or {}
    percent, team = state.get("percent"), state.get("team") or "your team"
    if percent is None:
        return ""
    if state.get("active"):
        return "%s %.0f%% to make the playoffs" % (team, percent)
    floor = league.get("race_min_odds")
    return "%s race hidden - %s at %.0f%% to make the playoffs (floor %d%%)" % (
        league["label"], team, percent, floor or 0)


def merge_into(config, today=None):
    """Add derived entries to config['watchlist'], keeping the sheet's rows."""
    added = []
    for league in config.get("leagues", []):
        if not league.get("enabled", True):
            continue
        entries = derive(config, league, today)
        if not entries:
            continue
        bucket = config.setdefault("watchlist", {}).setdefault(league["key"], [])
        existing = {(e.get("team") or "").lower() for e in bucket}
        for entry in entries:
            if entry["team"].lower() not in existing:
                bucket.append(entry)
                added.append("%s: %s (%s)" % (league["label"], entry["team"], entry["note"]))
    return added
