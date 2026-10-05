# flows/grammar.md: the fields, their status, the prompt and the schema

The grammar is one dict of `Field`s: `SEARCH` in `examples/movies/fields.py`, built with `search_grammar/grammar.py`. Everything the model reads about fields, and everything it may answer, is generated from it.

## A field

`Field(says, shape, status, why)`:

- `says`: what it means, in the words the model reads. Examples settle the distinctions ("'all' when every genre at once ('a crime drama')").
- `shape`: its JSON schema.
- `status`:
  - `ready`: code applies it (`resolve.py` must handle it).
  - `dictionary`: the model returns a neutral fact (`age: 6`); code holds what it means here (`AGE_EXCLUDES`, `AGE_REQUIRES`, `AUDIENCE` in `resolve.py`). The model never names a rating or a rule.
  - `later`: understood and parsed, not applicable yet. `why` is required; code reports it in `cannot`.

## What is generated from it

- `listing(SEARCH)`: the "THE FIELDS" block of the prompt.
- `schema(SEARCH, ...)`: the strict JSON schema of each query. Every property required, nothing else allowed, at every level.

Never write either by hand: they would drift from the fields.

## Changing a field

1. Edit `fields.py`.
2. `ready`: handle it in `resolve.py` (and in `matches` if it filters). `dictionary`: add its rule in `resolve.py`. `later`: give its `why`.
3. Run the tests. `test_grammar.py` fails when a `ready` field has no code, when a `later` field has no reason, when the schema is not strict, or when a field would let the model report failure.
4. The prompt changed: re-record the model answers (`flows/data.md`) and read the diff.

## Rules

- The grammar is wider than what the system can do. A wish with nowhere to go is a missing field, never a confession field.
- No field lets the model say something cannot be done.
