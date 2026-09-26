"""The model's side: read the sentence against the grammar, point. ONE call.

In the prompt, always: the rules, the grammar, the index of films, the offers dictionary. With the
sentence: the packs of the films it names, spotted and loaded by code before the call. The model
returns a structured object and never a sentence to show; code turns it into results.
"""
import json
import re

from search_grammar.grammar import listing, schema
from search_grammar.forgiving import similarity, spot
from search_grammar.llm import chat

from examples.movies.fields import PICK, SEARCH
from examples.movies.offers import DICTIONARY, index_line, pack

SLOTS = 2  # packs sent with one sentence

RULES = """\
READ, DO NOT JUDGE, AND NEVER REPORT FAILURE
  Fill every field the sentence asks for, best effort. There is no field to say something cannot be
  done and you must never try: code that knows the catalogue decides that afterwards. A wish that
  seems to fit nowhere goes in the closest field, never nowhere. An empty object is a correct answer
  for a sentence that asks for nothing.
  Name no rating code, no country's rules, no id. "for a 6 year old" is age 6.

NAMES AND TITLES
  Correct a spelling you recognise and complete a surname: "tarentino" is Quentin Tarantino. A name you
  do not recognise passes through as written. Titles pass through as typed, never translated.
  NEVER add a film or a person the sentence did not name. "a 90s Tom Hanks comedy" names no film:
  finding which films fit is the search's job, not yours. "tonight" and "now" are not an occasion.

ONE SENTENCE, ONE REQUEST, USUALLY
  "a French comedy from the 90s" is ONE request. A second appears only when wishes have different shapes
  and pairing them matters: "a comedy with De Niro or a drama with Kevin Costner" is TWO.
  label is the request in the viewer's words, four or five of them.

SIMILARITY IS NOT A FILM, A TOPIC IS NOT A GENRE
  "like Titanic" is similar_to. "the actors from Titanic" is a reference. "a heist movie" is topics
  [heist], not genre Crime.

PACKS AND PICKS
  The index lists every film covered: not on it means not covered. With the sentence come the packs of
  films whose title appears in it, each with the words it was matched on: what exists for each film
  and nothing else. Code matched words, not meaning. YOU decide from the sentence whether it names
  that film: "taken seriously" is not the film Taken, "not the cars kind" is not the film Cars. A pack
  is context, not a request: ignore the pack of a film the sentence does not name. When the sentence asks HOW to watch a
  film it names (an edition, a language, a price, a quality), add a pick: the film's m<n>, the
  family's f<n>, and a value for EVERY wish the sentence has (edition, quality, audio, sound), copied
  from what the family lists ("the long version" is the extended edition the pack names). A wish the
  family does not list is still written, as the viewer said it: code says what does not exist, never
  you. Point, never copy: no offer id, no price. Also fill the watch fields as usual."""

class Session:
    """What code holds for one request: the refs, the loaded packs. Never the model."""

    def __init__(self, catalog):
        self.catalog = catalog
        self.refs = {f"m{i}": f["id"] for i, f in enumerate(catalog.films, start=1)}
        self.ref_of = {fid: ref for ref, fid in self.refs.items()}
        self.loaded = {}  # film id -> (text, families), oldest first
        self.trace = []

    def index(self):
        return "\n".join(index_line(self.ref_of[f["id"]], f, len(self.catalog.offers.get(f["id"], [])))
                         for f in self.catalog.films)

    def preload(self, sentence):
        """Load the packs of the films the sentence names, before the one call."""
        films = [self.catalog.by_id[m.key] for m in spot(sentence, self.catalog.titles)]
        self.matched_on = {f["id"]: w for f in films for w in [self._words(sentence, f)] if w}
        # Three films called Titanic: load the best known, and let load() report the other two.
        best = {}
        for film in sorted(films, key=lambda f: -f["popularity"]):
            best.setdefault(film["title"].lower(), film)
        names = [f"{f['title']} ({f['year']})" for f in list(best.values())[:SLOTS]]
        return self.load(names) if names else ""

    @staticmethod
    def _words(sentence, film):
        """The words of the sentence that matched this film's title, shown to the model as evidence."""
        from search_grammar.forgiving import normalize
        words = normalize(sentence).split()
        for title in filter(None, (film["title"], film["title_fr"], film["original_title"])):
            target = normalize(title)
            size = len(target.split()) if target else 0
            for i in range(len(words) - size + 1):
                window = " ".join(words[i:i + size])
                if size and (window == target or similarity(window, target) >= 0.8):
                    return window
        return None

    def load(self, names):
        out = []
        for name in names:
            if name.strip() in self.refs:  # an index ref: the model pointing, not naming
                film = self.catalog.by_id[self.refs[name.strip()]]
                name = f"{film['title']} ({film['year']})"
            year = re.search(r"\((\d{4})\)\s*$", name)
            title = name[:year.start()].strip() if year else name
            match, _ = self.catalog.film(title, int(year.group(1)) if year else None)
            _, others = self.catalog.film(title)
            others = [o for o in others + ([match] if match else []) if match and o.key != match.key]
            if not match or match.band == "unsure":
                out.append(f"'{name}': not in the catalogue")
                self.trace.append(f"'{name}': not in the catalogue")
                continue
            film = self.catalog.by_id[match.key]
            text, families = pack(film, self.catalog.offers.get(film["id"], []))
            self.loaded.pop(film["id"], None)
            self.loaded[film["id"]] = (text, families)
            while len(self.loaded) > SLOTS:
                self.loaded.pop(next(iter(self.loaded)))
            also = [f"{self.ref_of[o.key]} {self.catalog.by_id[o.key]['title']} ({self.catalog.by_id[o.key]['year']})"
                    for o in others]
            note = f"\n(other films called that: {', '.join(also)})" if also else ""
            evidence = getattr(self, "matched_on", {}).get(film["id"])
            said = f"\n(matched on the words: \"{evidence}\")" if evidence else ""
            out.append(f"{self.ref_of[film['id']]} {text}{note}{said}")
            self.trace.append(f"loaded {self.ref_of[film['id']]} {film['title']} ({film['year']}), "
                              f"{len(families)} families" + (f"; also {', '.join(also)}" if also else ""))
        return "\n\n".join(out)


def instructions(session):
    genres = ", ".join(session.catalog.genres)
    return (f"Turn a viewer's sentence about what to watch into search parameters.\n\n"
            f"THE FIELDS\n{listing(SEARCH)}\n  picks{' ' * 16}pointers into a loaded pack, see PACKS AND PICKS\n\n"
            f"GENRES, use these words exactly: {genres}\n\n{RULES}\n\n"
            f"THE INDEX, every film covered\n{session.index()}\n\n{DICTIONARY}")


def answer_schema():
    query = schema(SEARCH, {"label": {"type": "string"}})
    return {"type": "object", "additionalProperties": False,
            "properties": {"queries": {"type": "array", "items": query}, "picks": PICK},
            "required": ["queries", "picks"]}


def ask(sentence, session):
    """ONE model call. The fixed prompt comes first so it is cached; the packs travel with the sentence."""
    packs = session.preload(sentence)
    user = f"SENTENCE: {sentence}" + (f"\n\nPACKS OF FILMS WHOSE TITLE APPEARS IN THE SENTENCE\n{packs}" if packs else "")
    messages = [{"role": "system", "content": instructions(session)}, {"role": "user", "content": user}]
    message, used = chat(messages, schema=answer_schema())
    return json.loads(message["content"]), [used]
