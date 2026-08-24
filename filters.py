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
TAG_LABELS = {
    "standalone": "Standalone",
    "national tv": "National Game",
    "ranked": "Ranked",
    "power": "Power Four",
    "tournament": "Tournament",
}
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
    names = [n for n in (game.get("tv") or []) if _flat(n) not in hidden]
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


def evaluate(game, league, config):
    """Returns (keep, tier, reasons). Also stamps the game dict."""
    rules = league.get("include") or {}
    sides = (game["home"], game["away"])
    reasons = []

    pinned = pinned_for(config, league["key"])
    fav_hit = any(_matches(t, f) for t in sides for f in pinned)

    # Both sides can be on the watchlist -- a game between the division leader
    # and the wild card holder is doubly interesting, and says so.
    watch_notes, watch_context = [], []
    for entry in watchlist_for(config, league["key"]):
        if any(_matches(t, entry.get("team")) for t in sides):
            note = entry.get("note") or "watchlist"
            if note not in watch_notes:
                watch_notes.append(note)
            if entry.get("context") and entry["context"] not in watch_context:
                watch_context.append(entry["context"])
    # Rule-driven Key opponents, alongside the sheet's manual watchlist.
    for rule in rules.get("tier3_rules") or []:
        if rule_matches(game, rule):
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
    if not tournament and _on_day(game, rules.get("power_conference_days"))             and matching_conference(game, rules.get("power_conferences")):
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

    game["tier"] = tier
    game["is_favorite"] = fav_hit
    game["watch_note"] = watch_note
    game["watch_notes"] = watch_notes
    game["watch_context"] = " · ".join(watch_context)
    game["reasons"] = reasons
    game["tags"] = tags_for(game)
    return keep, tier, reasons


def _postseason_tag(game):
    """'NFC Wild Card Playoffs' -> 'NFC Wild Card'; falls back to 'Playoff'."""
    headline = (game.get("note") or "").strip()
    if not headline:
        return "Playoff"
    for suffix in (" Playoffs", " Playoff"):
        if headline.endswith(suffix):
            return headline[: -len(suffix)]
    return headline


def tags_for(game):
    """Short labels saying why this game is on the page.

    Ordered most-specific first rather than by the order rules happened to
    fire, so the cap keeps the informative tag: why you personally care beats
    the playoff round, which beats how it is being broadcast.
    """
    reasons = game.get("reasons") or []
    tags = list(game.get("watch_notes") or [])
    if "postseason" in reasons:
        tags.append(_postseason_tag(game))
    ordered = [r for r in reasons if r.startswith("round:")]
    ordered += [r for r in reasons if r.startswith("note:")]
    ordered += ["tournament", "standalone", "national tv", "ranked", "power"]
    ordered += [r for r in reasons if r.startswith("conf:")]
    for reason in ordered:
        # Every playoff game is in its own window, so "Standalone" next to
        # "NFC Wild Card" says nothing.
        if reason == "standalone" and "postseason" in reasons:
            continue
        if reason in reasons:
            label = reason.split(":", 1)[1] if reason.startswith(("conf:", "round:", "note:"))                 else TAG_LABELS.get(reason)
            if label and label not in tags:
                tags.append(label)
    return tags[:MAX_TAGS]
