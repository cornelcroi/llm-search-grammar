# flows/packs.md: items with their own options

For catalogs where each item has options no model knows: here, each film's ways to watch (service, mode, edition, quality, audio, price). The layers come from `search_grammar/compact.py`; the movie version is `examples/movies/offers.py`; the pointers are checked in `examples/movies/picks.py`.

## The three layers

- **Index** (`index_line`): one line per film, always in the prompt: `m83 Titanic (1997) · 80 offers`. Enough to recognise it, nothing more. Not on the list means not covered.
- **Dictionary** (`DICTIONARY`): what every film shares, written once: modes, edition templates, qualities, language codes, services. Stable, so it sits in the cached prefix.
- **Pack** (`pack`): one film's own options, folded into families (`fold`, keyed on `FAMILY_KEY` = service and mode; the values in `FAMILY_SETS` become sets, prices a range). Sent only with a sentence that names the film (`flows/search.md`, step 1).

## Pointers

The model points into a pack: `{film: "m83", family: "f3", edition: "extended (+37 min)", ...}`. It never writes an offer id or a price.

`check(pick, session, named)`:

- `dropped`: the film was not loaded, the family does not exist, or the film was not named in the sentence (the model choosing on the viewer's behalf). Dropped by code whatever the prompt said, and the reason given.
- `strict`: an offer has every value asked for. Code returns its real id and price.
- `partial`: no offer has them all. Code returns the closest real offer and, for each missing wish, where it exists instead, or "nowhere for this film".

Editions match through the forgiving search (`CLOSE`), so "extended cut" finds "extended (+37 min)".

## Rules

- Offer ids and prices come from code, never from the model's text.
- Not in the pack means it does not exist for this film. Said as a fact.
