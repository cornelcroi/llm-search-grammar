# CLAUDE.md

Read this first. It is the index: where each part of the search lives, and the rules that keep the pattern true.
Load only the file the task needs, not the repo. (This is the [librarian pattern](https://corneliucroitoru.com/writing/librarian-pattern/), kept light: one flow, one index.)

## The flow: one sentence, one model call, code decides

```
sentence
  -> assistant.py   Session.preload: the forgiving search spots the films the sentence names, their packs are loaded
  -> assistant.py   ask: ONE call to the model, strict JSON schema generated from fields.py
  -> resolve.py     resolve: the model's words become catalog values; applied / cannot / unapplied / did_you_mean
  -> resolve.py     search: code runs the query; why_nothing when nothing matches
  -> picks.py       check: every pointer into a pack is checked; code owns offer ids and prices
  -> explain.py     every step as data; __main__.py prints it, web.py serves it
```

| You change | Read first | Then |
|---|---|---|
| what a person can ask (a field, its status) | `examples/movies/fields.py` | `search_grammar/grammar.py` builds the prompt listing and the schema from it; a `ready` field needs code in `resolve.py` (a test fails otherwise) |
| how loose words match the catalog | `search_grammar/forgiving.py` | `tests/test_forgiving.py` |
| how offers fold into packs | `search_grammar/compact.py`, `examples/movies/offers.py` | `measure.py` for the token counts |
| what code applies and refuses | `examples/movies/resolve.py` | `tests/test_movies.py` |
| the prompt | `examples/movies/assistant.py` | re-record the answers (below) and read the diff |
| what the terminal or the web shows | `examples/movies/explain.py` | both `__main__.py` and `web.py`/`web.html` read from it |
| the data | `scripts/build_catalog.py`, `scripts/generate_offers.py`, `scripts/add_posters.py` | the offers are invented on purpose; never present them as real |

## Rules

1. **Standard library only.** No dependency, in the engine, the demos or the tests. `certifi` is used when present, never required.
2. **The model never reports failure.** It has no `unsupported` or `cannot` field. Only code says "not applied", "cannot" or "nothing matches", with the reason. A wish with nowhere to go is a missing field in `fields.py`.
3. **The model points, code owns the ids.** Offer ids and prices never pass through the model's text. A pointer at a film the sentence did not name is dropped by code.
4. **The prompt listing and the schema are generated** from `fields.py`. Never write either by hand.
5. **Tests need no key.** They replay real model answers from `tests/answers.json`. After changing the prompt or the grammar: `OPENAI_API_KEY=... python3 scripts/record_answers.py`, read the diff, then run the tests. Add new sentences rather than re-recording old ones when the old answers still hold.
6. **Never commit a key.** `.env` is git-ignored; `.env.example` shows the variables. The TMDB token is only for `scripts/add_posters.py`; the demo loads posters without it.
7. **The README promises match the code.** Test counts, commands, numbers and the TMDB attribution are written in the README; change them together.

## Run

```bash
python3 -m unittest discover -s tests -t .      # no key
python3 -m examples.movies "a Truffaut film in French"
python3 -m examples.movies.web                  # http://127.0.0.1:8000
python3 -m examples.movies.measure Titanic      # no key
```
