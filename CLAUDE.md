# CLAUDE.md

Start from [`FLOWS.md`](FLOWS.md): the index of the flows, one line each. Open only the flow doc the task needs, not the repo.
Every source file names its flow doc in its first line (`FLOW-CRITICAL: implements flows/...`); read that doc before changing the file.
This is the [librarian pattern](https://corneliucroitoru.com/writing/librarian-pattern/): one index, one doc per flow, a header in each file, a hook that warns.

## Rules

1. **Standard library only.** No dependency, in the engine, the demos or the tests. `certifi` is used when present, never required.
2. **The model never reports failure.** It has no `unsupported` or `cannot` field. Only code says "not applied", "cannot" or "nothing matches", with the reason. A wish with nowhere to go is a missing field in `fields.py`.
3. **The model points, code owns the ids.** Offer ids and prices never pass through the model's text. A pointer at a film the sentence did not name is dropped by code.
4. **The prompt listing and the schema are generated** from `fields.py`. Never write either by hand.
5. **Tests need no key.** They replay real model answers from `tests/answers.json` (`flows/data.md`).
6. **Never commit a key.** `.env` is git-ignored; `.env.example` shows the variables.
7. **A change that alters a flow updates its doc in the same commit.** The hook warns when it doesn't: enable it once with `git config core.hooksPath scripts/hooks`.
8. **The README promises match the code.** Test counts, commands, numbers and the TMDB attribution change together with the code.

## Run

```bash
python3 -m unittest discover -s tests -t .      # no key
python3 -m examples.movies "a Truffaut film in French"
python3 -m examples.movies.web                  # http://127.0.0.1:8000
python3 -m examples.movies.measure Titanic      # no key
```
