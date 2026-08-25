"""Sports Daily: read the control sheet, fetch, filter, render the day.

    python sports_daily.py                 today, write output/today.html
    python sports_daily.py --date tomorrow
    python sports_daily.py --text          print to the console instead
    python sports_daily.py --check         validate the sheet's team names and exit
    python sports_daily.py --no-sheet      ignore the sheet, use config.json only
"""

import argparse
import difflib
import json
import os
import sys
import webbrowser
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import espn
import filters
import race
import render
import sheets

HERE = os.path.dirname(os.path.abspath(__file__))


def load_config(path=None):
    path = path or os.path.join(HERE, "config.json")
    # utf-8-sig: Notepad and PowerShell write a BOM that plain json rejects.
    with open(path, encoding="utf-8-sig") as fh:
        text = fh.read()
    try:
        return json.loads(text)
    except ValueError as exc:
        # Hand-editing JSON goes wrong in exactly two ways: a trailing comma
        # and a missing one. Show the line rather than a bare traceback.
        line = getattr(exc, "lineno", 0)
        context = text.splitlines()[line - 1].strip() if line else ""
        raise SystemExit(
            "config.json is not valid JSON: %s\n"
            "  line %s: %s\n"
            "  (usually a missing comma between entries, or a stray comma "
            "before a closing } or ])" % (exc, line, context))


def parse_day(raw, tz):
    today = datetime.now(tz).date()
    if not raw:
        return today
    lowered = raw.strip().lower()
    if lowered == "today":
        return today
    if lowered == "tomorrow":
        return today + timedelta(days=1)
    if lowered == "yesterday":
        return today - timedelta(days=1)
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%m/%d/%Y", "%m/%d"):
        try:
            parsed = datetime.strptime(raw, fmt)
            if fmt == "%m/%d":
                parsed = parsed.replace(year=today.year)
            return parsed.date()
        except ValueError:
            continue
    raise SystemExit("Could not read date: %s" % raw)


def check_names(config):
    """Validate every configured name against ESPN. Returns a problem count.

    Group-aware: a cup competition's team list holds only the clubs currently
    in it, so Tottenham is legitimately missing from the Europa League roster
    while playing in the Champions League. A name is only wrong if it resolves
    nowhere in its group.
    """
    seen = {}       # (group, tier, name) -> {"ok": [labels], "ambig": [...], "miss": [...]}
    rosters = {}
    for league in config.get("leagues", []):
        group = league.get("team_group") or league["key"]
        roster = rosters.setdefault(league["key"], espn.team_list(league))
        entries = [(t, "favorite") for t in filters.favorites_for(config, league["key"])]
        entries += [(t, "follow") for t in filters.following_for(config, league["key"])]
        entries += [(e.get("team"), "watch")
                    for e in filters.watchlist_for(config, league["key"])]
        for raw, tier in entries:
            record = seen.setdefault((group, tier, raw),
                                     {"ok": [], "ambig": [], "miss": [], "names": []})
            if not roster:
                continue
            record["names"] = record["names"] or [d for _, d in roster]
            matched = [display for abbr, display in roster
                       if filters._matches({"abbr": abbr, "name": display,
                                            "short": display}, raw)]
            if len(matched) > 1:
                record["ambig"].append((league["label"], matched))
            elif matched:
                record["ok"].append(league["label"])
            else:
                record["miss"].append(league["label"])

    problems = 0
    for (group, tier, raw), record in seen.items():
        if record["ambig"]:
            # Matching is substring, so "Michigan" also means Michigan State.
            problems += 1
            label, matched = record["ambig"][0]
            print("  AMBIG %-16s %-9s %s -- matches %d teams: %s" % (
                label, tier, raw, len(matched), ", ".join(matched[:4])))
        elif record["ok"]:
            where = record["ok"][0]
            extra = "" if not record["miss"] else                 "  (not in %s -- expected for cups)" % ", ".join(record["miss"][:2])
            print("  ok   %-16s %-9s %s%s" % (where, tier, raw, extra))
        else:
            problems += 1
            close = difflib.get_close_matches(raw, record["names"], n=2, cutoff=0.5)
            hint = (" -- did you mean %s?" % " / ".join(close)) if close else ""
            print("  BAD  %-16s %-9s %s%s" % (group, tier, raw, hint))
    return problems


def mark_standalone(games):
    """Stamp games that are the only one in their kickoff slot.

    This is how the NFL's standalone windows (TNF/SNF/MNF, Thanksgiving, the
    December Saturdays) are identified -- verified to catch all of them and to
    reject every regional Sunday-window game, with no network list to maintain.
    """
    slots = {}
    for game in games:
        slots[game["start_local"]] = slots.get(game["start_local"], 0) + 1
    for game in games:
        game["standalone"] = slots[game["start_local"]] == 1


HISTORY_COLUMNS = ["date", "team", "seed", "division", "wins", "losses", "points",
                   "clincher", "leads_division", "gap_to_division", "gap_to_last_spot"]


def record_history(config, day, tz):
    """Append one row per favorite per day to output/history/.

    Only ever writes for TODAY: browsing to another date must not stamp that
    date with standings that are current rather than historical. One row per
    team per day, so re-running is harmless.
    """
    if day != datetime.now(tz).date():
        return []
    written = []
    folder = os.path.join(HERE, "output", "history")
    os.makedirs(folder, exist_ok=True)
    for league in config.get("leagues", []):
        if not league.get("enabled", True) or not league.get("playoff_race"):
            continue
        snap = race.snapshot(config, league)
        if not snap:
            continue
        path = os.path.join(folder, "%s.csv" % league["key"])
        stamp = day.isoformat()
        existing = ""
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                existing = fh.read()
        if ("\n" + stamp + ",") in existing or existing.startswith(stamp + ","):
            continue
        row = dict(snap, date=stamp)
        with open(path, "a", encoding="utf-8", newline="") as fh:
            if not existing:
                fh.write(",".join(HISTORY_COLUMNS) + "\n")
            fh.write(",".join(str(row.get(c, "")).replace(",", " ")
                              for c in HISTORY_COLUMNS) + "\n")
        written.append("%s %s" % (league["label"], snap["team"]))
    return written


def collect(config, day, tz, only=None):
    """Fetch every enabled league and keep the games that pass its filters."""
    kept, stats = [], []
    date_key = day.strftime("%Y%m%d")
    for league in config.get("leagues", []):
        if not league.get("enabled", True):
            continue
        if only and league["key"] not in only:
            continue
        games = espn.games_for(league, date_key, tz,
                               cache_minutes=config.get("cache_minutes", 30))
        # ESPN answers by UTC date; a late West-coast game lands on the next
        # UTC day, so trust our own local-day comparison instead.
        games = [g for g in games if g["start_local"].date() == day]
        mark_standalone(games)
        passed = [g for g in games if filters.evaluate(g, league, config)[0]]
        kept.extend(passed)
        stats.append((league["label"], len(passed), len(games)))
    return kept, stats


def as_text(day, games, config, notes=None):
    lines = [day.strftime("%A, %B %d").replace(" 0", " "), ""]
    for note in notes or []:
        lines.append("  (%s)" % note)
    if notes:
        lines.append("")

    def line(game, with_league=True):
        when = game["start_local"].strftime("%I:%M %p").lstrip("0")
        if game["state"] == "in":
            when = game.get("status_detail") or "live"
        elif game["state"] == "post":
            when = "final"

        def side(team):
            rank = "#%d " % team["rank"] if team["rank"] else ""
            rec = " (%s)" % team["detail"] if (
                team.get("detail") and config.get("show_records", True)) else ""
            return "%s%s%s" % (rank, team["short"] or team["name"], rec)

        tail = []
        # The sport is obvious from the team except in soccer, where the same
        # club turns up across half a dozen competitions.
        if with_league and (game.get("sport") or "") == "Soccer":
            tail.append(game["league_label"])
        tail += game.get("tags") or []
        rnd = filters.round_label(game)
        if rnd:
            tail.insert(0, rnd)
        tail += filters.display_networks(game, config)
        if config.get("show_odds", True) and game["spread"]:
            tail.append(game["spread"])
        suffix = "  [%s]" % ", ".join(tail) if tail else ""
        if (game.get("sport") or "") == "Soccer":
            first, second, joiner = game["home"], game["away"], "vs"
        else:
            first, second, joiner = game["away"], game["home"], "at"
        if game.get("neutral"):
            joiner = "vs"          # nobody is "at" a neutral site
        detail = filters.detail_of(game)
        if detail:
            suffix = "%s  (%s)" % (suffix, detail)
        return "  %-9s %s %s %s%s" % (when, side(first), joiner, side(second), suffix)

    by_time = sorted(games, key=lambda g: g["start_local"])
    pinned = [g for g in by_time if g.get("tier") == "favorite"]
    if pinned:
        lines.append("MY TEAMS")
        lines += [line(g) for g in pinned]
        lines.append("")

    rivals = [g for g in by_time if g.get("tier") != "favorite" and g.get("rival")]
    if rivals:
        lines.append("RIVALS")
        lines += [line(g) for g in rivals]
        lines.append("")

    rank = {lg["label"]: lg.get("sort_rank", 99) for lg in config.get("leagues", [])}
    by_league = {}
    for game in by_time:
        if game.get("tier") != "favorite" and not game.get("rival"):
            by_league.setdefault(game["league_label"], []).append(game)
    order = sorted(by_league,
                   key=lambda label: (min(g["start_local"] for g in by_league[label]),
                                      rank.get(label, 99), label))
    for label in order:
        lines.append(label.upper())
        lines += [line(g, with_league=False) for g in by_league[label]]
        lines.append("")

    if not games:
        lines.append("  (nothing matches your filters today)")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Sports Daily")
    ap.add_argument("--date", help="YYYY-MM-DD, MM/DD, today, tomorrow, yesterday")
    ap.add_argument("--text", action="store_true", help="print instead of writing HTML")
    ap.add_argument("--open", action="store_true", help="open the HTML when done")
    ap.add_argument("--league", action="append", help="limit to a league key (repeatable)")
    ap.add_argument("--check", action="store_true",
                    help="validate the sheet's team names and exit")
    ap.add_argument("--no-sheet", action="store_true", help="ignore the control sheet")
    ap.add_argument("--config", help="path to an alternate config.json")
    ap.add_argument("--out", help="override the output path")
    args = ap.parse_args(argv)

    config = load_config(args.config)
    notes = sheets.load(config, use_sheet=not args.no_sheet)
    tz = ZoneInfo(config.get("timezone", "America/New_York"))
    day = parse_day(args.date, tz)
    only = set(args.league) if args.league else None

    # The race window follows the day being shown, not the day it is run, so
    # browsing to a November date shows November's race.
    race_log = race.merge_into(config, today=day)
    race_log += ["history: %s" % w for w in record_history(config, day, tz)]
    # Derived teams are console detail; the odds line goes on the page.
    info = [line for line in
            (race.status(lg) for lg in config.get("leagues", [])
             if not only or lg["key"] in only) if line]

    if args.check:
        print("Checking team names against ESPN...")
        problems = check_names(config)
        if problems:
            print("%d name%s need attention" %
                  (problems, " needs" if problems == 1 else "s need"))
        else:
            print("All names resolve.")
        return 1 if problems else 0

    games, stats = collect(config, day, tz, only=only)

    if args.text:
        print(as_text(day, games, config, notes + info))
    else:
        out = args.out or config.get("output", "output/today.html")
        if not os.path.isabs(out):
            out = os.path.join(HERE, out)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(render.render(day, games, config, notes=notes, info=info))
        print("wrote %s" % out)
        if args.open:
            webbrowser.open("file:///" + out.replace("\\", "/"))

    for line in race_log:
        print("  race: %s" % line)
    for note in notes + info:
        print("  note: %s" % note)
    shown = sum(s[1] for s in stats)
    found = sum(s[2] for s in stats)
    print("%s: %d of %d games kept" % (day.isoformat(), shown, found))
    for label, kept, total in stats:
        if total:
            print("  %-18s %3d / %-3d" % (label, kept, total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
