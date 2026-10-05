# flows/data.md: the data, and the answers the tests replay

## The films (`scripts/build_catalog.py`)

From Wikidata (CC0): the most-linked films (`MOST_LINKED`), plus French ones (`FRENCH`), plus three films called Titanic on purpose (`EXTRA`). Credits in Wikidata's order, the first `CAST_KEPT` actors. Writes `data/films.json`. Then run the posters and the offers again.

## The posters (`scripts/add_posters.py`)

Needs `TMDB_TOKEN` (free, never committed). The TMDB id comes from Wikidata (P4947), the poster path from TMDB. Only the path is stored in `data/films.json`; the web demo loads the image from TMDB's image server, so running the demo needs no TMDB key. The TMDB attribution stays in the README and the web page footer.

## The offers (`scripts/generate_offers.py`)

**Invented**: fictional services, made-up prices. They stand for any catalog where each item has its own options. Writes `data/offers.json`. Never present them as real.

## The recorded answers (`scripts/record_answers.py`)

The tests run without a key by replaying real model answers from `tests/answers.json`: for each sentence, the packs loaded and the answer exactly as returned.

- After changing the prompt or the grammar: `OPENAI_API_KEY=... python3 scripts/record_answers.py`, read the diff, then run the tests.
- A new behaviour gets a new sentence in `SENTENCES`. Keep old recordings when they still hold: a re-record can change an answer the tests depend on.

## Rules

- No key in the repo or its history: `.env` is git-ignored, `.env.example` shows the variables.
- The README's numbers (films, offers, tests) change with the data.
