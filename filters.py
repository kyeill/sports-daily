"""Which games make the brief, and which of the three buckets they land in.

  favorite   your teams -- always kept, always first
  watch      key opponents from the sheet's watchlist (rivals, playoff races)
  interest   everything else that passes a league's rules

A game is kept if ANY rule matches; the rules are OR-ed, never AND-ed, so
widening the config can only add games. A game shows up once, in its highest
bucket.
"""

import fnmatch
import re

import espn

TIERS = ("favorite", "watch", "interest")

# Internal reason -> the label shown on the page. "slate" has no entry on
# purpose: a game kept only because its whole league is shown would tag every
# row with the same word, which is noise, not information.
# The only notes that still earn a tag: they say something the row does not.
CHASE_NOTES = ("Division Chase", "Wild Card Chase", "Playoff Spot Chase")
MAX_TAGS = 2


def _flat(text):
    """Lowercase, alphanumerics and '+' -- 'SEC Network' -> 'secnetwork'.

    The '+' must survive: dropping it collapsed 'ESPN+' onto 'ESPN' and let
    every streaming-only game through the national-TV rule.
    """
    return "".join(c for c in (text or "").lower() if c.isalnum() or c == "+")


def _matches(team, entry):
    """Exact abbreviation, or the entry appearing in the team's name.

    Substring is deliberate ('Michigan' should catch 'Michigan Wolverines'),
    which means short entries over-match -- prefer the fuller name.
    """
    entry = (entry or "").strip().lower()
    if not entry:
        return False
    if entry == (team.get("abbr") or "").lower():
        return True
    return entry in (team.get("name") or "").lower() \
        or entry in (team.get("short") or "").lower()


def favorites_for(config, league_key):
    """Teams that drive the playoff race AND get pinned."""
    return [f for f in (config.get("favorites") or {}).get(league_key, []) if f]


def following_for(config, league_key):
    """Teams that get pinned but never drive the race -- tier 'follow'."""
    return [f for f in (config.get("following") or {}).get(league_key, []) if f]


def pinned_for(config, league_key):
    return favorites_for(config, league_key) + following_for(config, league_key)


def watchlist_for(config, league_key):
    """Watchlist entries: dicts of {team, note, expires}."""
    return (config.get("watchlist") or {}).get(league_key, [])


def display_networks(game, config, limit=1):
    """Networks worth printing: national ones first, junk dropped.

    Baseball lists MLB.TV plus both teams' regional feeds on every game, which
    crowds out the only entry that tells you anything (FOX, ESPN, ...).
    """
    hidden = {_flat(n) for n in (config.get("hide_networks") or [])}
    wanted = {_flat(n) for n in (config.get("national_networks") or [])}
    # Some leagues only want the national feed: a regional sports network tells
    # you nothing useful unless it happens to be the one you get.
    pool = game.get("tv_national") if game.get("national_only") else game.get("tv")
    names = [n for n in (pool or []) if _flat(n) not in hidden]
    # Streaming only earns a mention when it is the only way to watch: if a
    # game is on NBC there is no point also saying Peacock.
    streaming = {_flat(n) for n in (config.get("streaming_networks") or [])}
    on_tv = [n for n in names if _flat(n) not in streaming]
    if on_tv:
        names = on_tv
    names.sort(key=lambda n: 0 if _flat(n) in wanted else 1)
    # ESPN returns "SECN+" on some games and "SEC Network+" on others. The
    # short forms are the ones that fit the phone's column.
    renames = config.get("network_names") or {}
    return [renames.get(n, n) for n in names[:limit]]


def _on_day(game, days):
    """True when the game falls on one of the named days ('Sat', 'Fri', ...).

    An empty or missing list means every day, so a rule without a day filter
    behaves exactly as it did before.
    """
    if not days:
        return True
    wanted = {str(d).strip().lower()[:3] for d in days}
    return game["start_local"].strftime("%a").lower() in wanted


def on_networks(game, names):
    wanted = {_flat(n) for n in names or []}
    return any(_flat(name) in wanted for name in game.get("tv") or [])


def matching_conference(game, wanted):
    """The configured conference this game matches, or ''."""
    conf = (game.get("conference") or "").lower()
    if not conf:
        return ""
    for entry in wanted or []:
        if (entry or "").lower() in conf:
            return entry
    return ""


def on_national_network(game, config):
    """True only for the named broadcast networks.

    Deliberately NOT ESPN's own broadcasts[].market == 'national' flag: ESPN+
    is marked national and carries nearly everything, which made the rule
    meaningless when it was tried that way.
    """
    wanted = {_flat(n) for n in (config.get("national_networks") or [])}
    return any(_flat(name) in wanted for name in game.get("tv") or [])


def _round_name(headline):
    """'NCAA ... - South Region - Sweet 16' -> 'Sweet 16'."""
    return (headline or "").rsplit(" - ", 1)[-1].strip()


def postseason_reasons(game, rules):
    """Tier-2 reasons for a tournament game, or [].

    These REPLACE the regular-season rules rather than adding to them: in March
    every tournament team is ranked and on a major network, so leaving the
    normal rules on would pull in the entire bracket from day one.

    Rules are tried in order and the first one whose `match` and `require` both
    fit decides the game. `require` failing means "not this rule" rather than
    "not eligible", so an NIT game reading "NIT - 1st Round" falls past the
    NCAA rules to the one meant for it.
    """
    headline = game.get("note") or ""
    lowered = headline.lower()
    for rule in rules.get("postseason_rules") or []:
        require = rule.get("require")
        if require and require.lower() not in lowered:
            continue
        if not any(m.lower() in lowered for m in rule.get("match") or []):
            continue
        if rule.get("tag") == "prefix":
            label = headline.split(" - ", 1)[0].strip()
        else:
            label = rule.get("tag") or _round_name(headline)
        if rule.get("all"):
            return ["round:%s" % label]
        sides = (game["home"], game["away"])
        if matching_conference(game, rule.get("conferences")):
            return ["round:%s" % label]
        if any(_matches(t, name) for t in sides for name in rule.get("teams") or []):
            return ["round:%s" % label]
        return []
    return []


def _club_names(team):
    return {(team.get(k) or "").strip().lower() for k in ("name", "short", "abbr") if team.get(k)}


def rule_matches(game, rule):
    """One composite rule. Every condition present must hold (AND).

    Separate rules OR with each other, so the overall model is unchanged: a
    game is kept if any rule fits. Soccer needs the AND because "Champions
    League league phase featuring an English team" is two conditions, not one.
    """
    sides = (game["home"], game["away"])

    if rule.get("days") and not _on_day(game, rule["days"]):
        return False
    if rule.get("months") and game["start_local"].month not in rule["months"]:
        return False

    rounds = rule.get("round")
    if rounds:
        # Exact match with explicit wildcards, NOT substring: "final" as a
        # substring also matches "quarterfinals" and "semifinals", which would
        # quietly turn "semis and finals only" into the whole knockout stage.
        current = (game.get("round") or "").lower()
        if not current or not any(fnmatch.fnmatch(current, r.lower()) for r in rounds):
            return False

    teams = rule.get("teams")
    if teams and not any(_matches(t, name) for t in sides for name in teams):
        return False

    pool_path = rule.get("clubs_from")
    if pool_path:
        pool = espn.clubs_in(pool_path)
        if not pool or not any(_club_names(t) & pool for t in sides):
            return False

    top = rule.get("table_top")
    if top:
        table = espn.soccer_table(top.get("path"))
        limit = top.get("n", 5)
        ranks = [table.get(n) for t in sides for n in _club_names(t)]
        if not any(r and r <= limit for r in ranks):
            return False

    headline = rule.get("headline")
    if headline:
        # Rounds live in the note for the US leagues: "World Series - Game 1",
        # "Stanley Cup Final - Game 4". The season slug is only "post-season".
        current = (game.get("note") or "").lower()
        if not current or not any(h.lower() in current for h in headline):
            return False

    if rule.get("networks") and not on_networks(game, rule["networks"]):
        return False

    if rule.get("source") and (game.get("source") or "") != rule["source"]:
        return False

    return True


def is_exhibition(game):
    """Preseason or a friendly -- nothing at stake, in any sport.

    The US leagues mark it as season type 1; soccer has no such type, so the
    round slug carries it ("preseason", "friendly"). This is the one rule that
    SUBTRACTS: it drops a game even when a favorite is playing.
    """
    if game.get("season_type") == 1:
        return True
    marker = "%s %s" % (game.get("round") or "", game.get("note") or "")
    return "preseason" in marker.lower() or "friendly" in marker.lower()


_place_cache = {}


def _ordinal(n):
    if 10 <= n % 100 <= 20:
        return "%dth" % n
    return "%d%s" % (n, {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


def _division_places(league):
    """{team name: '2nd'} within its own division."""
    key = ("division", league["key"])
    if key not in _place_cache:
        groups = {}
        for row in espn.standings(league):
            if row.get("seed"):
                groups.setdefault(row["division"], []).append(row)
        places = {}
        for rows in groups.values():
            for spot, row in enumerate(sorted(rows, key=lambda r: r["seed"]), 1):
                places[row["team"].lower()] = _ordinal(spot)
        _place_cache[key] = places
    return _place_cache[key]


def _win_pct(row):
    wins = row.get("wins") or 0
    losses = row.get("losses") or 0
    ties = row.get("ties") or 0
    played = wins + losses + ties
    return (wins + 0.5 * ties) / played if played else 0.0


def _conference_places(league):
    """{team name: (place, seed)} within its conference or league.

    Place is by RECORD; seed is ESPN's playoff seed, and the two genuinely
    differ -- the NFL seeds division winners 1-4 regardless of record, so in
    2025 Pittsburgh held the 4 seed at 10-7 while Houston sat behind them at
    12-5. Hockey orders by points rather than win percentage.
    """
    key = ("conference", league["key"])
    if key not in _place_cache:
        by_points = (league.get("sport") or "").lower() == "hockey"
        groups = {}
        for row in espn.standings(league):
            groups.setdefault(row["conference"], []).append(row)
        places = {}
        for rows in groups.values():
            # Record first; equal records fall back to ESPN's own seed, which
            # already encodes the league's tiebreakers.
            ordered = sorted(
                rows,
                key=lambda r: (-((r.get("points") or 0) if by_points else _win_pct(r)),
                               r.get("seed") or 99))
            for spot, row in enumerate(ordered, 1):
                places[row["team"].lower()] = (spot, row.get("seed"))
        _place_cache[key] = places
    return _place_cache[key]


def _table_places(league):
    """{club name: '3rd'} from a league table."""
    key = ("table", league["key"])
    if key not in _place_cache:
        _place_cache[key] = {name: _ordinal(rank)
                             for name, rank in espn.soccer_table(league["path"]).items()}
    return _place_cache[key]


def _short_label(team, config):
    """The name a phone falls back to when the full one will not fit.

    ESPN's short name is usually right, but not always: it renders Nottingham
    Forest as "Nottm Forest" when "Forest" is what anyone would say.
    """
    overrides = config.get("team_short_names") or {}
    name = (team.get("name") or "").lower()
    for match, short in overrides.items():
        if match.lower() in name:
            return short
    return team.get("short") or ""


def _label(team, config, league=None):
    """The name to print, honouring any override.

    ESPN's short name is not always what people say: Tottenham comes back as
    "Spurs".
    """
    overrides = config.get("team_names") or {}
    name = (team.get("name") or "").lower()
    for match, label in overrides.items():
        if match.lower() in name:
            return label
    # College and soccer teams are known by school or club, and ESPN's short
    # name abbreviates exactly that part -- "Boise St", "W Michigan", "Nottm
    # Forest". Its `location` is the same name written out. Pro teams are the
    # other way round: short is the nickname ("Tigers"), location the city.
    if league and (("college" in (league.get("key") or ""))
                   or (league.get("sport") or "") == "Soccer"):
        if team.get("location"):
            name = team["location"]
            # "Atlanta United FC", "Inter Miami CF" -- the suffix says nothing
            # on a page where every club is a football club, and it costs
            # width where there is least of it. A leading "FC Dallas" stays.
            parts = name.split()
            if len(parts) > 1 and parts[-1] in ("FC", "CF", "SC"):
                name = " ".join(parts[:-1])
            return name
    return team.get("short") or team.get("name") or ""


def stamp_details(game, league, config):
    """What shows next to each team name: record, place, or nothing."""
    mode = league.get("team_detail", "record")
    for side in (game["home"], game["away"]):
        side["label"] = _label(side, config, league)
        # After the label, since the label falls back to this for pro teams.
        side["short"] = _short_label(side, config)
        if mode == "conference_place":
            found = _conference_places(league).get((side.get("name") or "").lower())
            place, seed = found if found else (None, None)
            if game.get("postseason"):
                # A regular-season place means nothing once the bracket starts.
                side["detail"] = "%d seed" % seed if seed else ""
            else:
                side["detail"] = _ordinal(place) if place else ""
        elif mode == "division_place":
            side["detail"] = _division_places(league).get((side.get("name") or "").lower(), "")
        elif mode == "table_place":
            side["detail"] = _table_places(league).get((side.get("name") or "").lower(), "")
        elif mode == "none":
            side["detail"] = ""
        else:
            side["detail"] = side.get("record") or ""


RIVAL_NOTE = "rival"


def _colour(team, config):
    """A team's stripe colour, honouring any override in config.

    ESPN's primary colour is not always the one people picture: Syracuse comes
    back navy, not orange.
    """
    overrides = config.get("team_colors") or {}
    name = (team.get("name") or "").lower()
    for label, value in overrides.items():
        if label.lower() in name:
            return value.lstrip("#")
    return team.get("color") or ""


def _conference_of(league, team):
    return espn.conference_names(league["path"]).get(team.get("conference_id"), "")


def _tint_fallback(game, sides, league, config):
    """Which side to colour when nobody involved is yours or notable.

    Two rooting rules. Conference comes FIRST: a ranked Big Ten team against an
    unranked outsider takes the Big Ten side. Only when both or neither are in
    the conference does the underdog rule decide.
    """
    rules = config.get("tint_rules") or {}

    wanted = [c.lower() for c in (rules.get("prefer_conference") or [])]
    if wanted:
        excluded = [e.lower() for e in (rules.get("conference_exclude") or [])]
        in_conf = [any(w in _conference_of(league, t).lower() for w in wanted)
                   for t in sides]
        if in_conf[0] != in_conf[1]:
            pick = sides[0] if in_conf[0] else sides[1]
            if not any(e in (pick.get("name") or "").lower() for e in excluded):
                return pick

    if rules.get("prefer_unranked"):
        ranked = [bool(t.get("rank")) for t in sides]
        if ranked[0] != ranked[1]:
            return sides[0] if not ranked[0] else sides[1]

    return game["home"]


def _preferred_sides(game, sides, league):
    """Sides whose own colour should win, if exactly one of them qualifies.

    Named clubs in the league (Liverpool, the Manchester pair) and, in the
    European competitions, any English club. Two of them in one game has no
    answer, so it falls through to the home side -- which is also why the
    domestic cups name nobody: both sides are English by definition.
    """
    found = []
    for name in league.get("tint_prefer_teams") or []:
        found.extend(t for t in sides if _matches(t, name) and t not in found)
    pool_path = league.get("tint_prefer_clubs_from")
    if pool_path:
        pool = espn.clubs_in(pool_path)
        found.extend(t for t in sides
                     if _club_names(t) & pool and t not in found)
    return found


def _tint(game, sides, pinned, notable, rivals, config, league):
    """The colour stripe.

    Your team wins outright. Against a rival the stripe takes the OTHER team's
    colour -- you are watching for the rival to lose. Any other team of
    interest (Syracuse, Arsenal, the last-spot holder) colours itself. Two
    rivals in one game has no honest answer, so it goes black.
    """
    mine = [t for t in sides if any(_matches(t, f) for f in pinned)]
    if mine:
        return _colour(mine[0], config)
    if len(rivals) > 1:
        return "000000"
    if rivals:
        other = [t for t in sides if t is not rivals[0]]
        if other:
            return _colour(other[0], config)
    preferred = _preferred_sides(game, sides, league)
    if len(preferred) == 1:
        return _colour(preferred[0], config)
    if preferred:
        return _colour(game["home"], config)     # two of them: no honest pick

    if len(notable) == 1:
        return _colour(notable[0], config)
    if notable:
        return _colour(game["home"], config)
    return _colour(_tint_fallback(game, sides, league, config), config)


def _spread_points(game):
    """The number of points in 'IU -40.5', or None."""
    match = re.search(r"-\s*(\d+(?:\.\d+)?)", game.get("spread") or "")
    return float(match.group(1)) if match else None


def is_blowout(game, league):
    """A game nobody expects to be competitive, and no reason to keep it.

    Only ever applied to the ordinary sections: your own teams and the
    highlights are never dropped for being lopsided.
    """
    limit = league.get("max_spread")
    if not limit:
        return False
    points = _spread_points(game)
    if points is None or points <= limit:
        return False

    sides = (game["home"], game["away"])
    for name in league.get("spread_exempt_teams") or []:
        if any(_matches(t, name) for t in sides):
            return False
    # The marquee windows are worth having on whatever the line says. The time
    # is matched with an hour of slack: these slots drift by a quarter-hour
    # from week to week, ABC's primetime moves between 7:30 and 8, and a
    # weather delay can push a start further still. Each network has only one
    # game in the window anyway, so the tolerance costs nothing.
    slack = league.get("spread_window_minutes", 60)
    start = game["start_local"].hour * 60 + game["start_local"].minute
    for slot in league.get("spread_exempt_windows") or []:
        hours, minutes = (slot.get("time") or "0:0").split(":")
        target = int(hours) * 60 + int(minutes)
        if (_on_day(game, slot.get("days")) and abs(start - target) <= slack
                and on_networks(game, [slot.get("network")])):
            return False
    return True


def evaluate(game, league, config):
    """Returns (keep, tier, reasons). Also stamps the game dict."""
    rules = league.get("include") or {}
    sides = (game["home"], game["away"])
    reasons = []

    pinned = pinned_for(config, league["key"])
    fav_hit = any(_matches(t, f) for t in sides for f in pinned)

    # Both sides can be on the watchlist -- a game between the division leader
    # and the wild card holder is doubly interesting, and says so.
    notable, rivals = [], []
    watch_notes, watch_context = [], []
    for entry in watchlist_for(config, league["key"]):
        hits = [t for t in sides if _matches(t, entry.get("team"))]
        notable.extend(t for t in hits if t not in notable)
        if (entry.get("note") or "").strip().lower() == RIVAL_NOTE:
            rivals.extend(t for t in hits if t not in rivals)
        if hits:
            note = entry.get("note") or "watchlist"
            if note not in watch_notes:
                watch_notes.append(note)
            if entry.get("context") and entry["context"] not in watch_context:
                watch_context.append(entry["context"])
    # Rule-driven Key opponents, alongside the sheet's manual watchlist.
    for rule in rules.get("tier3_rules") or []:
        if rule_matches(game, rule):
            for name in rule.get("teams") or []:
                hits = [t for t in sides if _matches(t, name)]
                notable.extend(t for t in hits if t not in notable)
                if rule.get("rival"):
                    rivals.extend(t for t in hits if t not in rivals)
            note = rule.get("note") or "watchlist"
            if note not in watch_notes:
                watch_notes.append(note)
    watch_note = watch_notes[0] if watch_notes else ""

    for rule in rules.get("rules") or []:
        if rule_matches(game, rule):
            reasons.append("note:%s" % (rule.get("note") or "match"))

    tournament = bool(game.get("postseason") and rules.get("postseason_rules"))
    if tournament:
        reasons += postseason_reasons(game, rules)

    if rules.get("all") and not tournament:
        reasons.append("slate")
    if not tournament and rules.get("standalone_only") and game.get("standalone"):
        reasons.append("standalone")
    if not tournament and rules.get("include_postseason") and game.get("postseason"):
        reasons.append("postseason")
    if not tournament and rules.get("national_tv") and on_national_network(game, config):
        reasons.append("national tv")
    within = None if tournament else rules.get("ranked_within")
    if within and any(t["rank"] and t["rank"] <= within for t in sides):
        reasons.append("ranked")

    # Conferences you always want, tagged with the conference that matched.
    conf_hit = "" if tournament else matching_conference(game, rules.get("conferences"))
    if conf_hit:
        reasons.append("conf:%s" % conf_hit)

    # Power conferences, but only on the days you asked for -- college
    # football's midweek games are a different proposition from Saturday's.
    if not tournament and rules.get("power_conferences")             and _on_day(game, rules.get("power_conference_days")):
        wanted = rules["power_conferences"]
        if rules.get("power_conferences_both"):
            # Both sides must be Power Four, so resolve each team's own
            # conference -- game["conference"] is the two joined together and
            # cannot tell "SEC vs Sun Belt" from "SEC vs ACC".
            names = espn.conference_names(league["path"])
            sides_conf = [names.get(t.get("conference_id"), "") for t in sides]
            hit = all(any(w.lower() in (c or "").lower() for w in wanted)
                      for c in sides_conf)
        else:
            hit = bool(matching_conference(game, wanted))
        if hit:
            reasons.append("power")

    # The big broadcast networks, likewise day-limited.
    if not tournament and rules.get("major_networks") and _on_day(game, rules.get("major_network_days"))             and on_networks(game, rules["major_networks"]):
        reasons.append("national tv")

    # Conference tournaments are regular season (type 2) in ESPN's data and
    # only identifiable by their headline; plain regular-season games have none.
    patterns = [p.lower() for p in (rules.get("note_matches") or [])]
    if patterns:
        headline = (game.get("note") or "").lower()
        if headline and any(p in headline for p in patterns):
            reasons.append("tournament")

    # Some of your own teams sit in Highlights rather than the main slate
    # unless the game actually matters -- a Tigers game in June. Postseason
    # promotes them back.
    # Soccer has no postseason flag, so a competition can nominate the rounds
    # that count as one: the Leagues Cup knockouts, every Concacaf round.
    promoted = bool(game.get("postseason"))
    if not promoted and league.get("promote_rounds"):
        current = (game.get("round") or "").lower()
        promoted = bool(current) and any(
            fnmatch.fnmatch(current, r.lower()) for r in league["promote_rounds"])

    demoted = False
    if fav_hit and not promoted:
        for name in league.get("highlight_teams") or []:
            if any(_matches(t, name) for t in sides):
                demoted = True
                break

    # A whole competition can live in Highlights -- every European club
    # fixture -- but never at the expense of your own team, who stays on the
    # main slate wherever they are playing.
    in_highlight_league = bool(league.get("highlight_all")) and not fav_hit

    if fav_hit and not demoted:
        tier = "favorite"
    elif fav_hit or watch_note or in_highlight_league:
        tier = "watch"
    else:
        tier = "interest"

    keep = bool(fav_hit or watch_note or reasons)
    if fav_hit and rules.get("favorites") is False:
        keep = bool(reasons)  # a league can opt out of favorite-forcing

    if config.get("hide_finished") and game.get("state") == "post" and tier == "interest":
        keep = False

    if config.get("exclude_exhibitions", True) and is_exhibition(game):
        keep = False

    if tier == "interest" and is_blowout(game, league):
        keep = False

    # Only a true favourite gets its regional feed; a "follow" team is pinned
    # but stays national-only.
    mine_side = ""
    for side_name in ("home", "away"):
        if any(_matches(game[side_name], f) for f in favorites_for(config, league["key"])):
            mine_side = side_name
            break
    game["my_side"] = mine_side
    stamp_details(game, league, config)
    game["tint"] = _tint(game, sides, pinned, notable, rivals, config, league)
    # Both a rival and a demoted favourite live in the Highlights block.
    game["highlight"] = bool(rivals) or demoted or in_highlight_league
    game["_league"] = league
    game["tier"] = tier
    game["is_favorite"] = fav_hit
    game["watch_note"] = watch_note
    game["watch_notes"] = watch_notes
    game["watch_context"] = " · ".join(watch_context)
    game["reasons"] = reasons
    game["tags"] = tags_for(game)
    return keep, tier, reasons


def _postseason_tag(game):
    """'World Series - Game 1' -> 'World Series'; 'NFC Wild Card Playoffs' -> 'NFC Wild Card'."""
    headline = (game.get("note") or "").strip()
    if not headline:
        return "Playoff"
    headline = headline.split(" - Game ")[0].strip()
    for suffix in (" Playoffs", " Playoff"):
        if headline.endswith(suffix):
            headline = headline[: -len(suffix)]
    return headline


# Whitelisted, not blacklisted: league slugs are unpredictable -- the Premier
# League calls its regular season "2025-26-english-premier-league", which a
# blacklist happily turned into a tag.
KNOCKOUT_WORDS = ("final", "semifinal", "quarterfinal", "round", "playoff",
                  "cup", "knockout", "3rd-place")


def _round_tag(game):
    """A readable round name from soccer's season slug, or ''.

    Soccer keeps the round in `season.slug` rather than the note, so a cup
    semi-final has nothing to label itself with unless we build it here.
    """
    slug = (game.get("round") or "").lower()
    if not slug or not any(w in slug for w in KNOCKOUT_WORDS):
        return ""
    # MLS uses "eastern-conference-playoffs---round-one"; the tail is the part
    # worth showing.
    slug = slug.split("---")[-1]
    words = [w for w in slug.replace("-", " ").split() if w]
    words = [w for w in words if w != "proper"]      # "Third Round Proper"
    # Europe's rounds are long; the short forms are what people say.
    joined = " ".join(words)
    if joined in ("round of 16", "round of 32"):
        return "R%s" % joined.rsplit(" ", 1)[1]
    small = ("of", "the", "and")
    pretty = " ".join(
        w.upper() if w in ("mls", "nit")
        else w if (w in small and i) else w.capitalize()
        for i, w in enumerate(words))
    return pretty


def _spell_out(label, config):
    """Numerals and league shorthand written the way people say them."""
    for short, full in (config.get("round_spellings") or {}).items():
        if label == short:
            return full
        if label.endswith(" " + short):          # "East 1st Round"
            return label[: -len(short)] + full
        if label.startswith(short + " "):
            return full + label[len(short):]
    return label


def round_label(game, config=None, league=None):
    """The round, shown beside the matchup: 'Second Round', 'World Series'."""
    reasons = game.get("reasons") or []
    explicit = [r.split(":", 1)[1] for r in reasons if r.startswith("round:")]
    if explicit:
        label = explicit[0]
    elif "postseason" in reasons:
        label = _postseason_tag(game)
    else:
        label = _round_tag(game)
    # Per-league wording: MLS calls its bracket "Playoffs Round One", and its
    # showpiece "MLS Cup Final" rather than plain "MLS Cup".
    for pattern, wording in ((league or {}).get("round_overrides") or {}).items():
        if fnmatch.fnmatch((game.get("round") or "").lower(), pattern.lower()):
            label = wording.replace("{round}", label)
            break
    if config:
        label = _spell_out(label, config)

    leg = leg_of(game)
    if label and leg:
        return "%s - %s" % (label, leg)
    return label or leg


def tags_for(game):
    """The short label on a row: why you care, or which round it is.

    Deliberately narrow. Tags that merely restate the section -- Ranked, Big
    Ten, National Game, Standalone -- were noise on every row, so the only
    survivors are the standings-derived chases and the round name.
    """
    # Only the standings-derived chases; the round sits beside the matchup.
    tags = [n for n in (game.get("watch_notes") or []) if n in CHASE_NOTES]
    return tags[:MAX_TAGS]


def leg_of(game):
    """'1st Leg' / '2nd Leg' for a two-legged European tie, else ''."""
    headline = (game.get("note") or "")
    for leg in ("1st Leg", "2nd Leg"):
        if headline.startswith(leg):
            return leg
    return ""


def _series_short(summary):
    """'LAD lead series 2-1' -> 'LAD 2-1'; 'Series tied 1-1' -> 'Tied 1-1'."""
    if not summary:
        return ""
    score = re.search(r"(\d+)-(\d+)", summary)
    if not score:
        return ""
    if "tied" in summary.lower():
        return "Tied %s" % score.group(0)
    who = re.match(r"^([A-Z][A-Za-z]{1,4})\b", summary.strip())
    return "%s %s" % (who.group(1), score.group(0)) if who else score.group(0)


def detail_of(game, config=None, league=None):
    """The single line under a matchup.

    Everything about the state of a tie belongs together rather than split
    across two lines: "World Series Gm 3 (LAD 2-1)".
    """
    headline = game.get("note") or ""
    lead = round_label(game, config, league)
    if " - Game " in headline:
        lead = ("%s Gm %s" % (lead, headline.split(" - Game ", 1)[1].strip())).strip()
    # ESPN also files a regular-season head-to-head under `series`, which read
    # as "(CLE 4-3)" on an ordinary November game -- indistinguishable from a
    # playoff series.
    series = _series_short(game.get("series")) if game.get("postseason") else ""
    if series:
        lead = ("%s (%s)" % (lead, series)).strip()

    if game.get("aggregate"):
        lead = ("%s (%s)" % (lead, game["aggregate"])).strip()

    parts = [lead]
    if game.get("watch_context"):
        parts.append(game["watch_context"])
    # A named round already says where you are; a bowl game does not also need
    # the stadium, nor a regional final its arena.
    if game.get("neutral") and game.get("venue") and not lead:
        parts.append(game["venue"])
    return " · ".join(p for p in parts if p)

