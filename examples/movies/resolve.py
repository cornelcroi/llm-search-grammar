"""Words into the catalogue. No model here: this is the half that knows the data.

Everything a viewer reads about what was done comes from here: `applied` is what code applied,
`cannot` what it understood and cannot do (with the grammar's reason), `unapplied` the words it
could not place, `did_you_mean` the matches too weak to apply, `relaxed` what was widened.
"""
from search_grammar.forgiving import find
from search_grammar.grammar import LATER

from examples.movies.fields import SEARCH

CODES = {"english": "en", "french": "fr", "german": "de", "spanish": "es", "italian": "it", "portuguese": "pt",
         "dutch": "nl", "polish": "pl", "romanian": "ro", "japanese": "ja", "russian": "ru", "swedish": "sv",
         "arabic": "ar"}
SLOT = {"lead_actor": 1, "lead_actors": 2, "actors": 4}

# The dictionary fields: the model says who is watching, code decides what that means HERE.
AGE_EXCLUDES = [(12, {"Horror", "Thriller", "Crime", "War"}), (16, {"Horror"})]
AGE_REQUIRES = [(10, {"Family", "Animation"})]  # a young child needs a film made for them, not just a mild one
AUDIENCE = {"kids": {"Family", "Animation"}, "children": {"Family", "Animation"}, "family": {"Family"},
            "teenagers": {"Adventure", "Comedy", "Science Fiction", "Fantasy"}}

# Widened in this order when nothing matches, never when the viewer said "only". Who, what and which
# language are never widened: a different person or genre is not a looser answer, it is another one.
RELAX = ["runtime_max", "max_price", "year_min", "year_max"]


class Catalog:
    def __init__(self, films, offers_by_film):
        self.films = films
        self.offers = offers_by_film
        self.titles = {f["id"]: [f["title"], f["title_fr"], f["original_title"]] for f in films}
        self.people = {name: [name] for f in films for name in f["cast"] + f["directors"]}
        self.topics = {t: [t] for f in films for t in f["topics"]}
        self.genres = sorted({g for f in films for g in f["genres"]})
        self.languages = {l.lower(): l for f in films for l in f["languages"]}
        self.by_id = {f["id"]: f for f in films}

    def film(self, title, year=None):
        """The best film for a title, the alternatives when several are equally good."""
        matches = [m for m in find(title, self.titles, limit=5)
                   if year is None or self.by_id[m.key]["year"] == year]
        if not matches:
            return None, []
        best = matches[0].score
        tied = sorted((m for m in matches if m.score == best), key=lambda m: -self.by_id[m.key]["popularity"])
        return tied[0], tied[1:]


def resolve(query, catalog):
    report = {"label": query.get("label", ""), "applied": {}, "unapplied": [], "cannot": {},
              "did_you_mean": [], "relaxed": []}
    filters = {}
    applied, unapplied = report["applied"], report["unapplied"]

    def take(match, word, into):
        if not match:
            unapplied.append(word)
            return None
        if match.band == "unsure":
            unapplied.append(word)
            report["did_you_mean"].append(match.name)
            return None
        applied.setdefault(into, []).append(match.name if match.band == "exact" else f"{match.name} (close to '{word}')")
        return match.key

    # which film ----------------------------------------------------------------------
    for wanted in query["films"]:
        match, others = catalog.film(wanted["title"], wanted["year"])
        key = take(match, wanted["title"], "films")
        if key:
            filters.setdefault("ids", set()).add(key)
            report["did_you_mean"] += [f"{catalog.by_id[o.key]['title']} ({catalog.by_id[o.key]['year']})" for o in others]

    # who ------------------------------------------------------------------------------
    for field, into in (("people", "cast"), ("directed_by", "director"), ("people_not", "cast_not")):
        for name in query[field]:
            matches = find(name, catalog.people, limit=1)
            key = take(matches[0] if matches else None, name, into)
            if key:
                filters.setdefault(into, set()).add(key)
    filters["cast_mode"] = query["cast_mode"]

    for ref in query["references"]:
        match, others = catalog.film(ref["film"])
        if not match or match.band == "unsure":
            unapplied.append(ref["film"])
            continue
        film = catalog.by_id[match.key]
        people = film["directors"] if ref["wants"] == "director" else film["cast"][:SLOT[ref["wants"]]]
        into = "director" if ref["wants"] == "director" else "cast"
        # The people are the filter, so the people are what is said back: never "as in Titanic".
        applied.setdefault(into, []).extend(people)
        applied.setdefault("through", []).append(f"{film['title']} ({film['year']})")
        filters.setdefault(into, set()).update(people)
        filters.setdefault("exclude", set()).add(film["id"])
        filters["cast_mode"] = "any"  # "actors from X" is any of them, whatever the sentence implied
        report["did_you_mean"] += [f"{catalog.by_id[o.key]['title']} ({catalog.by_id[o.key]['year']})" for o in others]

    # what about -----------------------------------------------------------------------
    for field, into in (("genre", "genre"), ("genre_not", "genre_not")):
        for word in query[field]:
            match = next((g for g in catalog.genres if g.lower() == word.lower()), None)
            if match:
                filters.setdefault(into, set()).add(match)
                applied.setdefault(into, []).append(match)
            else:
                unapplied.append(word)
    filters["genre_mode"] = query["genre_mode"]
    for field, into in (("topics", "topics"), ("topics_not", "topics_not")):
        for word in query[field]:
            matches = find(word, catalog.topics, limit=1)
            key = take(matches[0] if matches else None, word, into)
            if key:
                filters.setdefault(into, set()).add(key)

    # where from, when, how long ---------------------------------------------------------
    if query["language"]:
        # The model says the word; code finds what the catalogue calls it. The films' own languages,
        # not CODES: that table is for audio tracks, and a Korean film has no Korean audio offer here.
        name = catalog.languages.get(query["language"].strip().lower())
        if name:
            filters["language"] = name
            applied["language"] = name
        else:
            unapplied.append(query["language"])
    for field in ("country", "country_not", "year_min", "year_max", "runtime_max"):
        if query[field]:
            filters[field] = query[field]
            applied[field] = query[field]

    # who it is for: the dictionary fields ------------------------------------------------
    if query["age"] is not None:
        excluded = set().union(*(genres for limit, genres in AGE_EXCLUDES if query["age"] < limit))
        required = set().union(*(genres for limit, genres in AGE_REQUIRES if query["age"] < limit))
        if excluded:
            filters.setdefault("genre_not", set()).update(excluded)
        if required:
            filters.setdefault("audience", set()).update(required)
        if excluded or required:
            said = [f"{' or '.join(sorted(required))} only"] if required else []
            said += [f"no {', '.join(sorted(excluded))}"] if excluded else []
            applied["age"] = f"{query['age']}: " + "; ".join(said)
    for who in query["audience"]:
        genres = AUDIENCE.get(who.lower().strip())
        if genres:
            filters.setdefault("audience", set()).update(genres)
            applied.setdefault("audience", []).append(who)
        else:
            report["cannot"].setdefault("audience", {"why": "no dictionary entry for this viewer", "asked": []})
            report["cannot"]["audience"]["asked"].append(who)

    # how to watch: checked against each film's own offers ----------------------------------
    watch = {}
    for field in ("watch_mode", "quality", "services", "prefer", "max_price"):
        if query[field]:
            watch[field] = query[field]
            applied[field] = query[field]
    for field in ("audio", "subtitles"):
        codes = []
        for word in query[field]:
            code = CODES.get(word.lower().strip())
            if code:
                codes.append(code)
            elif field == "audio" and "original" in word.lower():
                codes.append("original")
            else:
                unapplied.append(word)
        if codes:
            watch[field] = codes
            applied[field] = codes
    if query["edition"]:
        watch["edition"] = query["edition"]
        applied["edition"] = query["edition"]

    # what this catalogue cannot do: parsed correctly, reported with the grammar's reason ---
    for name, field in SEARCH.items():
        value = query.get(name)
        if field.status == LATER and value not in (None, [], ""):
            report["cannot"][name] = {"why": field.why, "asked": value}

    filters["exact"] = query["exact"]
    return filters, watch, report


# --------------------------------------------------------------------------------------
# Applying the filters


def matches(film, f):
    if f.get("ids") and film["id"] not in f["ids"]:
        return False
    if film["id"] in f.get("exclude", ()):
        return False
    people = set(film["cast"])
    wanted = f.get("cast", set())
    if wanted and not (wanted <= people if f.get("cast_mode") == "all" else wanted & people):
        return False
    if f.get("director") and not f["director"] & set(film["directors"]):
        return False
    if f.get("cast_not") and f["cast_not"] & people:
        return False
    genres = set(film["genres"])
    if f.get("genre") and not (f["genre"] <= genres if f.get("genre_mode") == "all" else f["genre"] & genres):
        return False
    if f.get("genre_not") and f["genre_not"] & genres:
        return False
    if f.get("audience") and not f["audience"] & genres:
        return False
    if f.get("topics") and not f["topics"] & set(film["topics"]):
        return False
    if f.get("topics_not") and f["topics_not"] & set(film["topics"]):
        return False
    if f.get("language") and f["language"] not in film["languages"]:
        return False
    if f.get("country") and not set(f["country"]) & set(film["countries"]):
        return False
    if f.get("country_not") and set(f["country_not"]) & set(film["countries"]):
        return False
    if f.get("year_min") and film["year"] < f["year_min"]:
        return False
    if f.get("year_max") and film["year"] > f["year_max"]:
        return False
    if f.get("runtime_max") and film["runtime"] and film["runtime"] > f["runtime_max"]:
        return False
    return True


def ways_to_watch(film, offers, watch):
    """The film's offers that fit the viewer's watch wishes, best first."""
    original = offers[0]["audio"] if offers else None
    fits = []
    for o in offers:
        if watch.get("watch_mode") and o["mode"] not in watch["watch_mode"]:
            continue
        if watch.get("max_price") is not None and o["price"] > watch["max_price"]:
            continue
        if watch.get("quality") and o["quality"] not in watch["quality"]:
            continue
        if watch.get("services") and o["service"].lower() not in {s.lower() for s in watch["services"]}:
            continue
        if watch.get("audio") and not ({o["audio"]} & {original if a == "original" else a for a in watch["audio"]}):
            continue
        if watch.get("subtitles") and not set(watch["subtitles"]) <= set(o["subtitles"]):
            continue
        if watch.get("edition") and not find(" ".join(watch["edition"]), {o["edition"]: [o["edition"]]}):
            continue
        fits.append(o)
    rank = {"SD": 0, "HD": 1, "4K": 2}
    if watch.get("prefer") == "best_quality":
        fits.sort(key=lambda o: (-rank[o["quality"]], o["price"]))
    else:
        fits.sort(key=lambda o: (o["price"], -rank[o["quality"]]))
    return fits


def search(filters, watch, catalog, limit=5):
    """Films that match, and for each the best way to watch it when the viewer asked how."""
    relaxed = []
    active = dict(filters)
    active_watch = dict(watch)
    while True:
        found = []
        for film in catalog.films:
            if not matches(film, active):
                continue
            ways = ways_to_watch(film, catalog.offers.get(film["id"], []), active_watch) if active_watch else []
            if active_watch and not ways:
                continue
            found.append((film, ways))
        if found or filters.get("exact"):
            break
        loosen = next((k for k in RELAX if active.get(k) is not None or active_watch.get(k) is not None), None)
        if not loosen:
            relaxed = []  # widening found nothing either: nothing was relaxed into the answer
            break
        active.pop(loosen, None)
        active_watch.pop(loosen, None)
        relaxed.append(loosen)
    found.sort(key=lambda fw: (fw[1][0]["price"] if fw[1] and watch.get("prefer") == "cheapest" else 0,
                               -fw[0]["popularity"]))
    return found[:limit], len(found), relaxed


def why_nothing(filters, watch, catalog):
    """When nothing matched, say which wish emptied the list. An empty answer is never left unexplained."""
    films = [f for f in catalog.films if matches(f, filters)]
    if not films:
        return "no film in the catalogue matches the film wishes"
    if not watch:
        return None
    names = ", ".join(f"{f['title']} ({f['year']})" for f in films[:3]) + (" …" if len(films) > 3 else "")
    blocking = []
    for key, value in watch.items():
        if key == "prefer":
            continue
        if not any(ways_to_watch(f, catalog.offers.get(f["id"], []), {key: value}) for f in films):
            blocking.append(f"{key} {value}")
    if blocking:
        return f"{len(films)} film(s) match ({names}), but none can be watched with {' and '.join(blocking)}"
    return f"{len(films)} film(s) match ({names}), but no single offer has every watch wish at once"
