# FLOW-CRITICAL: implements flows/grammar.md
# Read the doc before changing behavior here; a change that alters the flow updates the doc in the same commit.
"""The movie grammar: every field a viewer can mean. The one place the search vocabulary exists.

Nothing here names a database column, a rating code or a service's internal id. The model reads a
sentence; code knows the catalogue.
"""
from search_grammar.grammar import DICTIONARY, LATER, Field, number, one_of, words

TITLES = {"type": "array", "items": {
    "type": "object", "additionalProperties": False,
    "properties": {"title": {"type": "string"}, "year": {"type": ["integer", "null"]}},
    "required": ["title", "year"]}}

SEARCH = {
    # ------------------------------------------------------------ which film
    "films": Field("a film named for any reason other than wanting something like it", TITLES),
    "similar_to": Field("films the viewer wants results LIKE: 'a movie like Forrest Gump'", TITLES,
                        LATER, "needs a similarity layer"),
    "type": Field("'series' when they ask for a series, null otherwise", one_of("series"), LATER,
                  "the catalogue holds films only"),

    # ------------------------------------------------------------ who
    "people": Field("people named with no role stated: 'with Tom Hanks'", words()),
    "directed_by": Field("people the sentence says DIRECTED it: 'directed by Kubrick', 'a Nolan film'", words()),
    "people_not": Field("people the viewer does not want: 'anything without Tom Cruise'", words()),
    "references": Field(
        "a person reached THROUGH a film rather than named: 'actors from Titanic', 'the director of Heat'",
        {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "properties": {"film": {"type": "string"},
                           "wants": {"type": "string", "enum": ["actors", "lead_actor", "lead_actors", "director"]}},
            "required": ["film", "wants"]}}),
    "people_nationality": Field("a nationality describing the PEOPLE: 'British actors'", words(), LATER,
                                "people's nationality is not in the catalogue"),

    # ------------------------------------------------------------ what about
    "genre": Field("genre words, only from the list given", words()),  # filled from the catalogue: see prompt
    "genre_not": Field("genres to exclude, ONLY when the sentence says not, no, without", words()),
    "genre_mode": Field("'all' when every genre at once ('a crime drama'), 'any' when either will do",
                        {"type": "string", "enum": ["any", "all"]}),
    "topics": Field("what the film is ABOUT, narrower than a genre and never flattened into one: heist, superhero",
                    words()),
    "topics_not": Field("topics to exclude: 'no superheroes'", words()),
    "mood": Field("how it should feel: cosy, feel-good, dark, tense", words(), LATER,
                  "no mood data in this catalogue"),

    # ------------------------------------------------------------ where from, when, how long
    "language": Field("the language a film is in, as a word: French, Italian", {"type": ["string", "null"]}),
    "country": Field("where the FILM is from, as ISO 3166-1 alpha-2, when a language cannot say it: GB, US",
                     words()),
    "country_not": Field("countries the film must not be from: 'not American'", words()),
    "year_min": Field("earliest year. 'the 90s' is 1990, 'recent' is 2015", number()),
    "year_max": Field("latest year. 'the 90s' is 1999, 'a classic' is 1990", number()),
    "runtime_max": Field("longest, in minutes. 'under two hours' is 120", number()),

    # ------------------------------------------------------------ who it is for, how regarded
    "age": Field("the age of the youngest person watching. A NUMBER, never a rating", number(), DICTIONARY),
    "audience": Field("who is watching, in the sentence's own words: kids, family, a first date", words(), DICTIONARY),
    "awards": Field("an award named: oscar, palme d'or", words(), LATER, "awards are not in the catalogue"),
    "occasion": Field("when or how it will be watched: a rainy sunday, background while cooking", words(), LATER,
                      "nothing in the catalogue answers it"),

    # ------------------------------------------------------------ how to watch
    "watch_mode": Field("how they want to watch: subscription, free, rent, buy",
                        {"type": "array", "items": {"type": "string", "enum": ["subscription", "free", "rent", "buy"]}}),
    "max_price": Field("the most they will pay, in euros. 'under 4 euros' is 4", {"type": ["number", "null"]}),
    "quality": Field("picture quality wanted: SD, HD, 4K",
                     {"type": "array", "items": {"type": "string", "enum": ["SD", "HD", "4K"]}}),
    "audio": Field("the language they want to HEAR, as a word: 'in French', 'the original voices'", words()),
    "subtitles": Field("subtitle languages wanted, as words", words()),
    "edition": Field("an edition in the viewer's words: 'the long version', 'with the director talking'", words()),
    "services": Field("services the viewer has or names: StreamOne, CinePass, RentBox", words()),
    "prefer": Field("'cheapest' or 'best_quality' when the sentence ranks the ways to watch",
                    one_of("cheapest", "best_quality")),

    # ------------------------------------------------------------ how to search
    "cast_mode": Field("'all' when everyone named must be in the same film, 'any' otherwise",
                       {"type": "string", "enum": ["any", "all"]}),
    "exact": Field("true only if the viewer insisted: only, must, exactly. It stops the search widening",
                   {"type": "boolean"}),
}

# A pick points into a LOADED pack: a film ref from the index, a family ref from its pack, and the
# values chosen among what that family lists. Never an offer id, never a price: code owns those.
PICK = {"type": "array", "items": {
    "type": "object", "additionalProperties": False,
    "properties": {
        "film": {"type": "string", "description": "m<n> from the index"},
        "family": {"type": "string", "description": "f<n> from that film's pack"},
        "edition": {"type": ["string", "null"]}, "quality": {"type": ["string", "null"]},
        "audio": {"type": ["string", "null"]}, "sound": {"type": ["string", "null"]},
    },
    "required": ["film", "family", "edition", "quality", "audio", "sound"]}}
