"""Build data/films.json from Wikidata (CC0: public domain, no attribution required).

    python3 scripts/build_catalog.py

Picks the most-linked films on Wikipedia, adds French films and a few chosen on purpose (two films
called Titanic, so a title can be ambiguous), then reads each one's credits in the order Wikidata
lists them, which is usually billing order. Only the standard library; certifi is used when present.
"""
import json
import re
import ssl
import time
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "films.json"
SPARQL = "https://query.wikidata.org/sparql"
API = "https://www.wikidata.org/w/api.php"
HEADERS = {"User-Agent": "llm-search-grammar/0.1 (https://github.com/cornelcroi/llm-search-grammar)"}

MOST_LINKED = 170
FRENCH = 30
CAST_KEPT = 8
BATCH = 50

# Chosen on purpose: three films called Titanic (1943, 1953, 1997), so a title can be ambiguous.
EXTRA = ["Q44578", "Q1197729", "Q679670"]

try:
    import certifi
    CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    CONTEXT = ssl.create_default_context()


def get(url, params):
    request = urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}", headers=HEADERS)
    with urllib.request.urlopen(request, context=CONTEXT, timeout=90) as response:
        return json.load(response)


def sparql_ids(query):
    rows = get(SPARQL, {"query": query, "format": "json"})["results"]["bindings"]
    return [row["film"]["value"].rsplit("/", 1)[1] for row in rows]


def top_films():
    most_linked = sparql_ids(f"""
        SELECT ?film WHERE {{
          ?film wdt:P31 wd:Q11424; wikibase:sitelinks ?links.
          FILTER(?links > 60)
        }} ORDER BY DESC(?links) LIMIT {MOST_LINKED}""")
    french = sparql_ids(f"""
        SELECT ?film WHERE {{
          ?film wdt:P31 wd:Q11424; wdt:P495 wd:Q142; wdt:P364 wd:Q150; wikibase:sitelinks ?links.
          FILTER(?links > 25)
        }} ORDER BY DESC(?links) LIMIT {FRENCH}""")
    return list(dict.fromkeys(most_linked + french + EXTRA))


def entities(ids, props="labels|claims"):
    found = {}
    for start in range(0, len(ids), BATCH):
        chunk = ids[start:start + BATCH]
        data = get(API, {"action": "wbgetentities", "ids": "|".join(chunk), "props": props,
                         "languages": "en|fr|mul", "format": "json"})
        found.update(data["entities"])
        time.sleep(0.5)
    return found


def values(entity, prop):
    out = []
    for claim in entity.get("claims", {}).get(prop, []):
        value = claim["mainsnak"].get("datavalue", {}).get("value")
        if value is not None:
            out.append(value)
    return out


def ids(entity, prop):
    return [v["id"] for v in values(entity, prop) if isinstance(v, dict) and "id" in v]


def label(entity, lang="en"):
    # Wikidata now keeps many names only under "mul" (one label for every language): James Cameron, Kate Winslet.
    labels = entity.get("labels", {})
    return (labels.get(lang) or labels.get("mul") or {}).get("value")


# Wikidata's genres are fine-grained and overlapping ("crime thriller", "neo-noir"). Each maps to broad
# genres; what is narrower than a genre ("heist", "superhero") becomes a topic, never flattened into one.
GENRES = {
    "Action": ["action", "martial arts", "swashbuckler"],
    "Adventure": ["adventure"],
    "Animation": ["animat"],
    "Comedy": ["comedy", "parody", "satir"],
    "Crime": ["crime", "gangster", "heist", "noir", "mafia", "detective"],
    "Documentary": ["documentary"],
    "Drama": ["drama", "melodrama"],
    "Family": ["family", "children"],
    "Fantasy": ["fantasy", "fairy tale", "sword and sorcery"],
    "History": ["historical", "history", "biographical", "period"],
    "Horror": ["horror", "slasher", "zombie", "monster"],
    "Music": ["music"],
    "Mystery": ["mystery", "whodunit"],
    "Romance": ["romance", "romantic"],
    "Science Fiction": ["science fiction", "sci-fi", "cyberpunk", "space opera", "dystopian", "post-apocalyptic"],
    "Thriller": ["thriller", "suspense"],
    "War": ["war"],
    "Western": ["western"],
}
NOT_TOPICS = {"flashback", "independent", "film based on literature", "film based on a novel", "drama", "comedy",
              "action", "adventure", "thriller", "romance", "fantasy", "horror", "war", "western", "mystery",
              "science fiction", "crime", "documentary", "animated", "historical", "biographical"}


def genres_and_topics(raw_terms):
    genres, topics = set(), set()
    for term in raw_terms:
        low = term.lower()
        matched = {g for g, words in GENRES.items() if any(w in low for w in words)}
        genres |= matched
        # "crime thriller" is two genres, not a topic; "psychological thriller" says something they do not.
        rest = low
        for words in (GENRES[g] for g in matched):
            for w in words:
                rest = rest.replace(w, " ")
        if low not in NOT_TOPICS and any(len(word) > 2 for word in re.findall(r"[a-z]+", rest)):
            topics.add(low)
    return sorted(genres), sorted(topics)


def year(entity):
    dates = [v["time"] for v in values(entity, "P577") if isinstance(v, dict) and "time" in v]
    years = [int(d[1:5]) for d in dates if d[1:5].isdigit()]
    return min(years) if years else None


def runtime(entity):
    for v in values(entity, "P2047"):
        amount = float(v["amount"])
        if v.get("unit", "").endswith("Q7727"):  # minutes
            return round(amount)
    return None


def main():
    film_ids = top_films()
    films = entities(film_ids, props="labels|claims|sitelinks")

    referenced = set()
    for film in films.values():
        for prop in ("P57", "P161", "P136", "P495", "P364"):
            referenced.update(ids(film, prop)[:CAST_KEPT] if prop == "P161" else ids(film, prop))
    names = entities(sorted(referenced), props="labels|claims")

    def name(qid):
        return label(names.get(qid, {})) if qid in names else None

    catalog = []
    for qid in film_ids:
        film = films.get(qid)
        if not film or not label(film):
            continue
        titles = [t["text"] for t in values(film, "P1476") if isinstance(t, dict)]
        countries = []
        for c in ids(film, "P495"):
            codes = [v for v in values(names.get(c, {}), "P297") if isinstance(v, str)]
            if codes:
                countries.append(codes[0])
        raw = [g.removesuffix(" film").removesuffix(" movie") for g in map(name, ids(film, "P136")) if g]
        genres, topics = genres_and_topics(raw)
        catalog.append({
            "id": qid,
            # How many Wikipedias have an article on it: the tie-break between three films called Titanic.
            "popularity": len(film.get("sitelinks", {})),
            "title": label(film),
            "title_fr": label(film, "fr"),
            "original_title": titles[0] if titles else None,
            "year": year(film),
            "runtime": runtime(film),
            "directors": [n for n in map(name, ids(film, "P57")) if n],
            "cast": [n for n in map(name, ids(film, "P161")[:CAST_KEPT]) if n],
            "genres": genres,
            "topics": topics,
            "countries": countries,
            "languages": [n for n in map(name, ids(film, "P364")) if n],
        })

    catalog.sort(key=lambda f: (f["year"] or 0, f["title"]))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(catalog, ensure_ascii=False, indent=1) + "\n")
    print(f"{len(catalog)} films -> {OUT}")


if __name__ == "__main__":
    main()
