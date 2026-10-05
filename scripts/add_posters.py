# FLOW-CRITICAL: implements flows/data.md
# Read the doc before changing behavior here; a change that alters the flow updates the doc in the same commit.
"""Add each film's TMDB id and poster path to data/films.json, for the web demo.

    TMDB_TOKEN=... python3 scripts/add_posters.py

The TMDB id comes from Wikidata (property P4947), the poster path from the TMDB API. Only the path is
stored; the web page loads the image from TMDB's image server, so running the demo needs no TMDB key.
Get a token (free, "API Read Access Token") at https://www.themoviedb.org/settings/api.
This product uses the TMDB API but is not endorsed or certified by TMDB.
"""
import json
import os
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

FILMS = Path(__file__).resolve().parent.parent / "data" / "films.json"
SPARQL = "https://query.wikidata.org/sparql"
TMDB = "https://api.themoviedb.org/3/movie/{}"
HEADERS = {"User-Agent": "llm-search-grammar/0.1 (https://github.com/cornelcroi/llm-search-grammar)"}

try:
    import certifi
    CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    CONTEXT = ssl.create_default_context()


def get(url, headers):
    request = urllib.request.Request(url, headers={**HEADERS, **headers})
    with urllib.request.urlopen(request, context=CONTEXT, timeout=60) as response:
        return json.load(response)


def tmdb_ids(qids):
    """Wikidata id -> TMDB movie id, in one query."""
    values = " ".join(f"wd:{q}" for q in qids)
    query = f"SELECT ?film ?tmdb WHERE {{ VALUES ?film {{ {values} }} ?film wdt:P4947 ?tmdb . }}"
    data = get(f"{SPARQL}?{urllib.parse.urlencode({'query': query, 'format': 'json'})}", {})
    return {row["film"]["value"].rsplit("/", 1)[1]: row["tmdb"]["value"] for row in data["results"]["bindings"]}


def main():
    token = os.environ.get("TMDB_TOKEN")
    if not token:
        sys.exit("TMDB_TOKEN is not set. Get a free API Read Access Token at https://www.themoviedb.org/settings/api.")
    films = json.loads(FILMS.read_text())
    ids = tmdb_ids([f["id"] for f in films])
    missing = []
    for film in films:
        tmdb = ids.get(film["id"])
        if not tmdb:
            missing.append(film["title"])
            continue
        data = get(TMDB.format(tmdb), {"Authorization": f"Bearer {token}", "accept": "application/json"})
        film["tmdb_id"] = int(tmdb)
        film["poster"] = data.get("poster_path")
        time.sleep(0.05)  # well under TMDB's rate limit
    FILMS.write_text(json.dumps(films, ensure_ascii=False, indent=1) + "\n")
    with_poster = sum(1 for f in films if f.get("poster"))
    print(f"{with_poster} of {len(films)} films have a poster. No TMDB id on Wikidata: {missing or 'none'}")


if __name__ == "__main__":
    main()
