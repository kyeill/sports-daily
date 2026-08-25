"""Which games make the brief, and which of the three buckets they land in.

  favorite   your teams -- always kept, always first
  watch      key opponents from the sheet's watchlist (rivals, playoff races)
  interest   everything else that passes a league's rules

A game is kept if ANY rule matches; the rules are OR-ed, never AND-ed, so
widening the config can only add games. A game shows up once, in its highest
bucket.
"""

import fnmatch

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


def display_networks(game, config, limit=2):
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
    # If a game is on NBC there is no point also saying Peacock; it only earns
    # a mention when it is the only way to watch.
    for main, redundant in (config.get("network_supersedes") or {}).items():
        if any(_flat(n) == _flat(main) for n in names):
            names = [n for n in names
                     if not any(_flat(n) == _flat(r) for r in redundant)]
    names.sort(key=lambda n: 0 if _flat(n) in wanted else 1)
    return names[:limit]


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


def _table_places(league):
    """{club name: '3rd'} from a league table."""
    key = ("table", league["key"])
    if key not in _place_cache:
        _place_cache[key] = {name: _ordinal(rank)
                             for name, rank in espn.soccer_table(league["path"]).items()}
    return _place_cache[key]


def stamp_details(game, league):
    """What shows next to each team name: record, place, or nothing."""
    mode = league.get("team_detail", "record")
    for side in (game["home"], game["away"]):
        if mode == "division_place":
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


def _tint(game, sides, pinned, notable, rivals, config):
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
    if notable:
        return _colour(notable[0], config)
    return _colour(game["home"], config)


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
                notable.extend(t for t in sides
                               if _matches(t, name) and t not in notable)
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

    if fav_hit:
        tier = "favorite"
    elif watch_note:
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

    stamp_details(game, league)
    game["tint"] = _tint(game, sides, pinned, notable, rivals, config)
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
KNOCKOUT_WORDS = ("final", "semifinal", "quarterfinal", "round-of", "playoff",
                  "cup", "knockout", "3rd-place", "round-one", "round-two")


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
    small = ("of", "the", "and")
    pretty = " ".join(
        w.upper() if w in ("mls", "nit")
        else w if (w in small and i) else w.capitalize()
        for i, w in enumerate(words))
    return pretty


def tags_for(game):
    """The short label on a row: why you care, or which round it is.

    Deliberately narrow. Tags that merely restate the section -- Ranked, Big
    Ten, National Game, Standalone -- were noise on every row, so the only
    survivors are the standings-derived chases and the round name.
    """
    tags = [n for n in (game.get("watch_notes") or []) if n in CHASE_NOTES]

    reasons = game.get("reasons") or []
    # Explicit round labels set by postseason_rules (March Madness, the NIT).
    tags += [r.split(":", 1)[1] for r in reasons if r.startswith("round:")]

    if "postseason" in reasons:
        label = _postseason_tag(game)
    else:
        label = _round_tag(game)
    leg = leg_of(game)
    if label and leg:
        label = "%s %s" % (label, leg)
    elif not label and leg:
        label = leg
    if label and label not in tags:
        tags.append(label)

    return tags[:MAX_TAGS]


def leg_of(game):
    """'1st Leg' / '2nd Leg' for a two-legged European tie, else ''."""
    headline = (game.get("note") or "")
    for leg in ("1st Leg", "2nd Leg"):
        if headline.startswith(leg):
            return leg
    return ""


def detail_of(game):
    """The line under a matchup: series state, aggregate, game number."""
    parts = []
    if game.get("watch_context"):
        parts.append(game["watch_context"])
    headline = game.get("note") or ""
    if " - Game " in headline:
        parts.append("Game " + headline.split(" - Game ", 1)[1].strip())
    if game.get("series"):
        parts.append(game["series"])
    # "2nd Leg - Arsenal advance 3-1 on aggregate" -> the aggregate half
    if leg_of(game) and " - " in headline:
        parts.append(headline.split(" - ", 1)[1].strip())
    return " · ".join(p for p in parts if p)

