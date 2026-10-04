# llm-search-grammar: the search grammar pattern

**Natural language search with LLMs, over a catalog the model has never seen. The search grammar pattern describes the offer by its dimensions, not its rows. The model reads. Code decides.**

It's not the prompt. It's the grammar.

The full story, with diagrams and a live demo: [The Search Grammar Pattern: Natural Language Search with LLMs](https://corneliucroitoru.com/writing/search-grammar-pattern/).

## Live demo

[![The search grammar pattern, live: Tonight answering 9 real searches, one small LLM call each](docs/demo.png)](https://youtu.be/hoCesxy2o08)

This is Tonight, my movie app at home, running the search grammar pattern on its real catalog: 9 searches, every result checked. This repo rebuilds the pattern on 200 films, so you can run it and read it.

## What is the search grammar pattern?

A pattern for putting a language model in front of a search, when every item in the catalog has its own large set of options that no model knows.

The model never searches, never picks an id, never says "sorry, I can't". It reads the sentence against a **grammar**: a compact description of everything that can be asked and everything that exists. Code does the rest, and says exactly what it did.

I found it while building Tonight, a movie app I use at home: say what you feel like watching, get films you can start now, across all my streaming services. This repo rebuilds the pattern on 200 films, small enough to read in ten minutes, with invented offers so each film has its own options no model has seen.

## The problem

Ask a model what you can watch tonight. It answers with what it knows: "Titanic is probably on Netflix." It does not know your catalog. It cannot: your offer is different for every film, and it changes.

The usual fixes make it worse:

- **Put everything in the prompt.** 17,262 offers here is ~400,000 tokens. Every request.
- **Give it tools and hope.** It decides when to search, what to call things, and what is "not supported". You can only ask it to behave.
- **Add a line to the prompt every time it answers badly.** Every fix is one more instruction to the same overloaded model.

Everything you hand the model, you can only ask. Everything you keep in code, you can guarantee.

## The grammar

Two parts. One says what a person can **mean**. The other says what **exists**.

### What a person can mean: the fields

One file (`examples/movies/fields.py`) defines every field a viewer can mean: what it means, its shape, and a **status**.

```
ready        code applies it today                       people, genre, years, audio, price...
dictionary   the model says a neutral fact, code knows   age 6  ->  what a 6-year-old may watch HERE
             what it means here
later        understood, not possible yet, with a reason  "like Forrest Gump"  ->  needs a similarity layer
```

The grammar is **wider than what the system can do**. The model parses everything a person might want. Nothing is silently dropped: what code cannot apply comes back as `cannot`, with the reason. And the list of `cannot` is your roadmap, sorted by what people actually ask.

The prompt's field list and the strict JSON schema are both **generated** from that file. They cannot drift apart.

### What exists: index, dictionary, packs

```
INDEX        one line per film, always in the prompt        m83 Titanic (1997) · 80 offers
             not on the list = not covered

DICTIONARY   what every film shares, written ONCE           modes, qualities, languages, edition templates:
             cached, paid once                               {director}'s cut · extended (+{m} min) · ...

PACK         one film's own options, folded into            f3 RentBox · rent · 25th anniversary/Cameron's cut/
             families, loaded when the sentence names it               extended (+37 min)/theatrical · HD/SD · ...
```

Two compressions make it small:

- **Families.** Offers that differ only in a few values become one line: the values become sets, the prices a range. 19 offers per line, here.
- **Sharing.** What every film has in common is written once in the dictionary, never repeated in a pack.

The pack is where the model learns what it could not know. Titanic (1997) has a *Cameron's cut* and an *extended (+37 min)*. The 1953 Titanic has a *commentary by Clifton Webb*. No model has seen those. No fuzzy match turns "nolan talking over it" into "with commentary by Christopher Nolan": they score 0.26. The model, reading the dictionary and the pack, does.

## The rules

1. **The model never reports failure.** No `unsupported` field. It parses, best effort. Only code says "no match", "not possible", "doesn't exist", because only code knows the data. A wish with nowhere to go is a missing field, never a model confession.
2. **One model call.** Before it, code spots the films the sentence names (typos, other languages, three films called Titanic), loads their lines, and sends them with the sentence, each with the words it matched on. The model decides whether a film is really named: "taken seriously" is not the film *Taken*. The fixed part of the prompt comes first, so it is cached.
3. **The model points, code owns the ids.** It answers `film m83, family f3, edition "extended (+37 min)"`. Never an offer id, never a price. Code finds the real offer.
4. **Certainty comes from the pack.** The dictionary says what exists in general, the pack says what exists here. Not in the pack means it does not exist for this film. Said as a fact, not a guess.
5. **Make the machine forgive.** Accents, typos, surnames, any language: code tolerates loose words, and says how sure it is in a word (exact, close, unsure), never a number.
6. **Say back what code did.** `applied`, `cannot` (with the reason), `unapplied`, `did_you_mean`, `relaxed`, and when nothing matches, `why_nothing`. What the model claimed is never shown.
7. **Trust structure, not model discipline.** A pointer at a film the sentence did not name is dropped by code, whatever the prompt said.

## See it run

Real output, `gpt-6-luna`, reasoning off:

```
$ python3 -m examples.movies "inceptoin with nolan talking over it"

1 · CODE loads the lines of the films the sentence names, then ONE call to gpt-6-luna
    code    loaded m142 Inception (2010), 3 families
    parsed  {"films": [{"title": "Inception", "year": 2010}], "edition": ["with commentary by Christopher Nolan"], "label": "Inception with Nolan commentary"}
    points  {"film": "m142", "family": "f2", "edition": "with commentary by Christopher Nolan"}

2 · CODE, decides what can be applied
    applied      {"films": ["Inception"], "edition": ["with commentary by Christopher Nolan"]}
    why_nothing  "1 film(s) match (Inception (2010)), but none can be watched with edition ['with commentary by Christopher Nolan']"

4 · POINTERS, checked against the pack by code
    partial  Inception (2010) · RentBox · rent · theatrical · SD · audio en · stereo · 2.99 €  [of11110]
             missing  edition with commentary by Christopher Nolan (not with RentBox rent; nowhere for this film)

1 model call · 5,492 prompt tokens · 265 completion tokens
```

One call. "inceptoin" was found by code before the call. "nolan talking over it" became the dictionary's `with commentary by {person}`, which no fuzzy match could reach. Then code checked Inception's pack and said it plainly: that version is nowhere for this film. The offer id and the price came from code.

```
$ python3 -m examples.movies "a cosy film like Forrest Gump for my 6 year old, without Tom Cruise"

1 · THE MODEL (gpt-6-luna), reads the sentence against the grammar
    parsed  {"similar_to": [{"title": "Forrest Gump"}], "people_not": ["Tom Cruise"], "mood": ["cosy"], "age": 6}

2 · CODE, decides what can be applied
    applied      {"cast_not": ["Tom Cruise"], "age": "6: Animation or Family only; no Crime, Horror, Thriller, War"}
    cannot       {"similar_to": {"why": "needs a similarity layer"}, "mood": {"why": "no mood data in this catalogue"}}
```

Every wish kept. Two applied, two refused with the reason. The model said "6"; code decided what that means here.

## The numbers

```
$ python3 -m examples.movies.measure

200 films, 17,262 offers (invented)

Everything, the naive way
  one line per offer               396,929 tokens

The grammar
  index, one line per film           2,123 tokens   always in the prompt
  dictionary, written once             224 tokens   always in the prompt, cached
  one pack, median                     164 tokens   sent when the sentence names the film
  offers per film, median               72  -> families 5

A request with two films loaded      2,676 tokens, against 396,929 to carry every offer
```

Token counts from `measure` are estimates, one token per 4 characters. **Be careful with these.** The offers are invented, so I chose how repetitive they are. The ratio illustrates the mechanism; it is not a finding about real catalogs. What carries over is the structure: an index, a dictionary written once, packs sent when the sentence names the item.

Measured with no model at all. A gain you can measure without the model belongs to the architecture, and survives every model swap.

## Use it in your domain

The core (`search_grammar/`) knows nothing about movies. Per domain you write four things: the fields, the index line, the dictionary, how to fold a pack.

| | Real estate | Application logs | Online shop |
|---|---|---|---|
| **index** | one line per listing: area, rooms, price | one line per service | one line per product |
| **dictionary** | energy ratings, legal floor-area rules, what "T3" means | log levels, environments, the time words | sizes, materials, delivery modes |
| **pack** | this flat's own features: floor, lift, balcony, charges | this service's own endpoints and error codes | this product's own variants, stock, prices |
| **a `dictionary` field** | "a family of four" -> 3 bedrooms, decided by code | "last night" -> a time range, computed by code | "for running" -> the right categories |
| **a `later` field** | "a quiet street" -> needs noise data | "slow requests" -> needs latency data | "looks like this photo" -> needs image search |

The question is always the same: what does each item have that no model can know? That goes in the pack.

## What's in the repo

```
search_grammar/        the pattern, no domain in it
  grammar.py           fields with a status -> the prompt listing and the strict schema; the agreement check
  compact.py           folding options into families
  forgiving.py         loose words -> the real thing, with exact / close / unsure
  llm.py               one call to the model, standard library only
examples/movies/
  fields.py            the movie grammar
  offers.py            index line, dictionary, pack
  assistant.py         the prompt, the lines of the films named, the one call
  resolve.py           words into the catalog: applied, cannot, why nothing
  picks.py             pointers checked against the pack: strict, partial, dropped
  measure.py           the numbers, no model
data/
  films.json           200 real films from Wikidata (CC0)
  offers.json          17,262 INVENTED ways to watch them: fictional services, made-up prices
scripts/               rebuild the data, record model answers for the tests
tests/                 27 tests, no API key needed: real model answers replayed through code
```

## Run it

Python 3.10+. No dependencies.

```bash
export OPENAI_API_KEY=...
python3 -m examples.movies "something with the actors from Titanic, in 4K"
python3 -m examples.movies.measure Titanic
python3 -m unittest discover -s tests -t .
```

`OPENAI_MODEL` changes the model. The default is `gpt-6-luna`, a small, cheap one, with reasoning off: reading a sentence against a grammar is classification, not reasoning.

## Prior art

The front half is not new. LangChain's self-query retriever, LlamaIndex auto-retrieval and Typesense's natural-language search turn a sentence into filters from a described schema. Resolving the model's words to ids in code is what Lex slot synonyms and text-to-SQL value linking do. Slot filling (Lex, Dialogflow, Rasa) is the ancestor, and it sends anything out of scope to a fallback.

What I did not find written up is the other half: a grammar deliberately wider than what the system can do, with each field's status stated, where the model is never asked whether something is possible; a compact index, dictionary and packs sent when the sentence names the item; and code reporting what it applied, what it could not, and why.

## Limits

- The offers are invented. Real catalogs are messier, and less repetitive.
- Ranking is basic: popularity, or price. The grammar decides what matches, not what is best.
- Every capability is code you write. Moving a field from `later` to `ready` is work, not a prompt edit. That is the point, and the cost.
- The model can still misread a sentence. It can no longer invent a film, an offer or a price.

## Licence

MIT. Films from Wikidata, public domain.
