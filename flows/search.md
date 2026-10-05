# flows/search.md: one sentence, end to end

Trigger: `explain(sentence, session)` in `examples/movies/explain.py`, called by the terminal demo (`__main__.py`) and the web demo (`web.py`, `GET /search?q=`). One `Session` per search.

## The steps, in order

1. **Spot the films named** (`Session.preload`, `assistant.py`). The forgiving search runs over every title (English, French, original) and finds the ones the sentence names. For a title shared by several films, the best known is loaded and the others are named as "other films called that". At most `SLOTS = 2` packs travel with one sentence. Each loaded film is recorded in `session.trace`.
2. **One model call** (`ask`, `assistant.py`). System prompt: `instructions(session)`, which is the grammar listing, the genres, the rules, the index and the dictionary; it never changes between requests, so it is cached. User message: the sentence, plus the packs from step 1 with the words they matched on. The answer must follow `answer_schema()` (strict JSON): `queries` (the fields filled) and `picks` (pointers into a pack).
3. **Resolve** (`resolve`, `resolve.py`). For each query, the model's words become catalog values:
   - names (`people`, `directed_by`, `people_not`) through the forgiving search over all people;
   - `references` (`{film, wants}`): find the film, then take its directors or the first `SLOT[wants]` names of its cast (`lead_actor` 1, `lead_actors` 2, `actors` 4); the film itself is excluded;
   - `genre` against the catalog's genre words; `topics` through the forgiving search; `language` against the films' languages;
   - `dictionary` fields (`age`, `audience`) through code's own rules;
   - `later` fields go to `cannot`, with the reason.
   Output: `filters`, `watch` (how to watch), and a report: `applied`, `cannot`, `unapplied`, `did_you_mean`.
4. **Query** (`search`, `resolve.py`). Every film is checked against the filters (`matches`). If nothing matches and the viewer did not insist (`exact`), the search widens one wish at a time in a fixed order (`RELAX`), never on who, what or which language, and says what it loosened (`relaxed`). Results sort by price when asked (`prefer: cheapest`), then popularity. Nothing found: `why_nothing` names the wish that emptied the list.
5. **Pointers** (`check`, `picks.py`): see `flows/packs.md`.
6. **Explain** (`explain.py`). Every step as data: `trace`, `queries` (`parsed`, `report`, `films` with poster and way to watch), `picks`, `usage`.

## Rules this flow keeps

- One model call per sentence. Nothing before it calls a model.
- The model never reports failure. `cannot`, `unapplied`, `why_nothing` come from code only.
- An empty answer is never left unexplained.
- A missing `OPENAI_API_KEY` or a failed call ends as a message (`SystemExit` in `llm.py`), shown by the web demo as an error, never a crash.
